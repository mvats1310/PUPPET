#include "generic_tp_controller.hpp"

#include <pluginlib/class_list_macros.h>
#include <std_msgs/Int32.h>

namespace tiago_telepresence_controllers
{

class GripperController : public StepperController<std_msgs::Int32>
{
public:
    GripperController() : StepperController("gripper") { }

protected:
    void processData(const std_msgs::Int32& msg) override
    {
        const auto value = static_cast<double>(msg.data);
        accept({value, value});
    }
};

} // namespace tiago_telepresence_controllers

PLUGINLIB_EXPORT_CLASS(tiago_telepresence_controllers::GripperController, controller_interface::ControllerBase);
