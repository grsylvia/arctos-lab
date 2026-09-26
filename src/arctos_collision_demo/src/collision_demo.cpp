#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <visualization_msgs/msg/marker_array.hpp>
#include <moveit/planning_scene/planning_scene.hpp>
#include <geometric_shapes/shapes.h>
#include <urdf_parser/urdf_parser.h>
#include <srdfdom/model.h>
#include <array>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>

using Marker = visualization_msgs::msg::Marker;
struct Block { const char* name; double x, y, z; };
// Fixed 8 cm cubes sit near the tool's sweep, in base_link coordinates (metres).
const std::array<Block, 3> blocks = {{{"block_1", .35, .16, .56},
                                     {"block_2", .35, -.16, .56},
                                     {"block_3", .46, 0., .42}}};

class CollisionDemo : public rclcpp::Node
{
public:
  CollisionDemo() : Node("arctos_collision_demo")
  {
    const auto path = declare_parameter<std::string>("model", "");
    std::ifstream input(path);
    if (!input) throw std::runtime_error("Cannot open URDF: " + path);
    std::stringstream xml;
    xml << input.rdbuf();
    auto urdf = urdf::parseURDF(xml.str());
    if (!urdf) throw std::runtime_error("Invalid URDF");
    auto srdf = std::make_shared<srdf::Model>();
    // No pairs are exempted: assembly contacts remain visible for review.
    if (!srdf->initString(*urdf, "<robot name='arctos'/>") )
      throw std::runtime_error("Invalid SRDF");
    scene_ = std::make_shared<planning_scene::PlanningScene>(urdf, srdf);
    state().setToDefaultValues();
    state().update();
    if (scene_->getRobotModel()->getLinkModelsWithCollisionGeometry().size() != 7)
      throw std::runtime_error("Expected seven links with loaded collision geometry");
    if (declare_parameter<bool>("verify", false))
    {
      verify();
      verified_ = true;
      return;
    }
    for (const auto& block : blocks) addBox(block.name, block.x, block.y, block.z, .08);
    publisher_ = create_publisher<visualization_msgs::msg::MarkerArray>(
        "collision_markers", rclcpp::QoS(1).transient_local());
    subscription_ = create_subscription<sensor_msgs::msg::JointState>(
        "joint_states", 1, [this](const sensor_msgs::msg::JointState& msg) {
          if (msg.name.size() != msg.position.size()) return;
          std::set<std::string> received;
          const auto& variables = scene_->getRobotModel()->getVariableNames();
          for (size_t i = 0; i < msg.name.size(); ++i)
            if (std::find(variables.begin(), variables.end(), msg.name[i]) != variables.end() && std::isfinite(msg.position[i]))
            {
              state().setVariablePosition(msg.name[i], msg.position[i]);
              received.insert(msg.name[i]);
            }
          if (received.size() != scene_->getRobotModel()->getVariableCount()) return;
          state().update();
          last_state_ = now();
          have_state_ = true;
        });
    timer_ = create_wall_timer(std::chrono::milliseconds(200), [this] { publish(); });
  }
  bool verified() const { return verified_; }

private:
  moveit::core::RobotState& state() { return scene_->getCurrentStateNonConst(); }
  void addBox(const std::string& name, double x, double y, double z, double size)
  {
    Eigen::Isometry3d pose = Eigen::Isometry3d::Identity();
    pose.translation() = Eigen::Vector3d(x, y, z);
    scene_->getWorldNonConst()->addToObject(name, std::make_shared<shapes::Box>(size, size, size), pose);
  }
  collision_detection::CollisionResult check(bool self)
  {
    collision_detection::CollisionRequest request;
    request.contacts = true;
    request.max_contacts = 100;
    request.max_contacts_per_pair = 1;
    collision_detection::CollisionResult result;
    if (self) scene_->checkSelfCollision(request, result);
    else scene_->getCollisionEnv()->checkRobotCollision(request, result, state());
    return result;
  }
  void verify()
  {
    if (check(false).collision) throw std::runtime_error("Empty world reported collision");
    addBox("probe", 5., 5., 5., .08);
    if (check(false).collision) throw std::runtime_error("Distant block reported collision");
    scene_->getWorldNonConst()->removeObject("probe");
    const auto tool = state().getGlobalLinkTransform("tool_link").translation().eval();
    addBox("probe", tool.x(), tool.y(), tool.z(), .12);
    if (!check(false).collision) throw std::runtime_error("Overlapping block was not detected");
    scene_->getWorldNonConst()->removeObject("probe");
    if (check(false).collision) throw std::runtime_error("Removed block still collides");
    RCLCPP_INFO(get_logger(), "PASS: empty, distant, overlapping, and removed obstacle checks");
    const auto self = check(true);
    for (const auto& entry : self.contacts)
      RCLCPP_INFO(get_logger(), "Zero-pose self contact: %s / %s", entry.first.first.c_str(), entry.first.second.c_str());
  }
  Marker marker(int id, int type)
  {
    Marker m;
    m.header.frame_id = "base_link";
    m.header.stamp = now();
    m.ns = "collision_verification";
    m.id = id;
    m.type = type;
    m.pose.orientation.w = 1.;
    m.color.a = 1.;
    return m;
  }
  void publish()
  {
    const bool fresh = have_state_ && (now() - last_state_).seconds() < 2.;
    collision_detection::CollisionResult world, self;
    if (fresh) { world = check(false); self = check(true); }
    std::set<std::string> hit;
    std::string pairs;
    Marker contacts = marker(4, Marker::SPHERE_LIST);
    contacts.scale.x = contacts.scale.y = contacts.scale.z = .015;
    contacts.color.r = 1.;
    for (const auto* result : {&world, &self})
      for (const auto& entry : result->contacts)
      {
        hit.insert(entry.first.first);
        hit.insert(entry.first.second);
        pairs += "\n" + entry.first.first + " / " + entry.first.second;
        for (const auto& contact : entry.second)
        {
          geometry_msgs::msg::Point point;
          point.x = contact.pos.x(); point.y = contact.pos.y(); point.z = contact.pos.z();
          contacts.points.push_back(point);
        }
      }
    visualization_msgs::msg::MarkerArray array;
    for (size_t i = 0; i < blocks.size(); ++i)
    {
      const auto& b = blocks[i];
      auto cube = marker(i, Marker::CUBE);
      cube.pose.position.x = b.x; cube.pose.position.y = b.y; cube.pose.position.z = b.z;
      cube.scale.x = cube.scale.y = cube.scale.z = .08;
      cube.color.r = hit.count(b.name) ? 1. : .2;
      cube.color.g = hit.count(b.name) ? .1 : .65;
      cube.color.b = hit.count(b.name) ? .1 : 1.;
      cube.color.a = .7;
      array.markers.push_back(cube);
    }
    auto label = marker(3, Marker::TEXT_VIEW_FACING);
    label.pose.position.z = .85;
    label.scale.z = .025;
    label.color.r = label.color.g = label.color.b = 1.;
    label.text = !fresh ? "Waiting for current joint states" :
        std::string("Blocks: ") + (world.collision ? "CONTACT" : "clear") +
        " | Self: " + (self.collision ? "CONTACT" : "clear") + pairs;
    if (fresh && !state().satisfiesBounds()) label.text += "\nOutside joint limits";
    if (label.text != last_report_)
    {
      RCLCPP_INFO(get_logger(), "%s", label.text.c_str());
      last_report_ = label.text;
    }
    if (contacts.points.empty()) contacts.action = Marker::DELETE;
    array.markers.push_back(label);
    array.markers.push_back(contacts);
    publisher_->publish(array);
  }
  planning_scene::PlanningScenePtr scene_;
  rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr publisher_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Time last_state_{0, 0, RCL_ROS_TIME};
  bool have_state_ = false, verified_ = false;
  std::string last_report_;
};

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  try
  {
    auto node = std::make_shared<CollisionDemo>();
    if (!node->verified()) rclcpp::spin(node);
  }
  catch (const std::exception& error)
  {
    RCLCPP_ERROR(rclcpp::get_logger("collision_demo"), "%s", error.what());
    rclcpp::shutdown();
    return 1;
  }
  rclcpp::shutdown();
  return 0;
}
