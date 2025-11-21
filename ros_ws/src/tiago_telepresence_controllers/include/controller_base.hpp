#ifndef __TIAGO_TP_CONTROLLER_BASE_HPP__
#define __TIAGO_TP_CONTROLLER_BASE_HPP__

#include <mutex>
#include <string>
#include <utility> // std::pair
#include <vector>
#include <controller_interface/controller.h>
#include <hardware_interface/joint_command_interface.h>

namespace tiago_telepresence_controllers
{

constexpr auto UPDATE_LOG_THROTTLE = 1.0; // [s]

class ControllerBase : public controller_interface::Controller<hardware_interface::PositionJointInterface>
{
public:
    ControllerBase(const std::string &_name) : name(_name) {}
    virtual ~ControllerBase() = default;
    bool init(hardware_interface::PositionJointInterface* hw, ros::NodeHandle &n) final override;
    void update(const ros::Time& time, const ros::Duration& period) final override;

protected:
    const std::vector<std::pair<double, double>> & getJointLimits() const { return jointLimits; }
    virtual bool additionalSetup(hardware_interface::PositionJointInterface* hw, ros::NodeHandle &n, const std::string &description) { return true; }
    virtual void registerSubscriber(ros::NodeHandle &n, ros::Subscriber &sub) = 0;
    virtual std::vector<double> getDesiredJointValues(const std::vector<double> & current, double period) = 0;
    virtual void onStarting(const std::vector<double> & angles) {}
    virtual void onDisabling() {}
    virtual void updateStatus(int & status) {}
    void updateStamp();
    int numJoints() const { return joints.size(); }
    const std::string & getName() const { return name; }

private:
    void registerPublisher(ros::NodeHandle &n, ros::Publisher &pub);
    ros::Time getLastStamp() const;

    ros::Subscriber sub;
    ros::Publisher pub;
    std::string name;
    bool isActive {false};
    std::vector<hardware_interface::JointHandle> joints;
    std::vector<std::pair<double, double>> jointLimits;
    ros::Time stamp;
    ros::Duration statePublishThrottle;
    ros::Time lastStatePublish;
    bool notifyOutOfLimits {false};

    mutable std::mutex stampMutex;
};

} // namespace tiago_telepresence_controllers

#endif // __TIAGO_TP_CONTROLLER_BASE_HPP__
