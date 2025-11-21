#include "generic_tp_controller.hpp"

#include <pluginlib/class_list_macros.h>
#include <geometry_msgs/QuaternionStamped.h>
#include <kdl/frames.hpp>

namespace tiago_telepresence_controllers
{

class HeadController : public JointBufferController<geometry_msgs::QuaternionStamped>
{
public:
    HeadController() : JointBufferController("head"), q(2) { }

protected:
    void processData(const geometry_msgs::QuaternionStamped& msg) override
    {
        const auto rot = KDL::Rotation::Quaternion(msg.quaternion.x, msg.quaternion.y, msg.quaternion.z, msg.quaternion.w);
        rot.GetEulerZYX(alpha, beta, gamma); // R_z_alpha * R_y_beta * R_x_gamma
        q(0) = -beta;
        q(1) = -gamma;
        accept(q, msg.header.stamp);
    }

private:
    KDL::JntArray q;
    double alpha, beta, gamma;
};

} // namespace tiago_telepresence_controllers

PLUGINLIB_EXPORT_CLASS(tiago_telepresence_controllers::HeadController, controller_interface::ControllerBase);
