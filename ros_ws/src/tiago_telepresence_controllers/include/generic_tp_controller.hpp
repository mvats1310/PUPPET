#ifndef __TIAGO_GENERIC_TP_CONTROLLER_HPP__
#define __TIAGO_GENERIC_TP_CONTROLLER_HPP__

#include <algorithm> // std::transform
#include <mutex>

#include "controller_base.hpp"
#include "command_buffer.hpp"

namespace tiago_telepresence_controllers
{

inline KDL::JntArray jointVectorToKdl(const std::vector<double> & v)
{
    // https://forum.kde.org/viewtopic.php%3Ff=74&t=94839.html#p331301
    KDL::JntArray ret;
    ret.data = Eigen::VectorXd::Map(v.data(), v.size());
    return ret;
}

inline std::vector<double> kdlToJointVector(const KDL::JntArray & q)
{
    // https://stackoverflow.com/a/26094702
    const auto & priv = q.data;
    return std::vector<double>(priv.data(), priv.data() + priv.rows());
}

template <typename T>
class GenericController : public ControllerBase
{
public:
    using ControllerBase::ControllerBase;

protected:
    void registerSubscriber(ros::NodeHandle &n, ros::Subscriber &sub) final override
    {
        sub = n.subscribe<T>("command", 1, &GenericController::callback, this);
    }

    virtual void processData(const T& msg) = 0;

private:
    void callback(const typename T::ConstPtr& msg)
    {
        updateStamp();
        processData(*msg);
    }
};

template <typename T, typename B>
class BufferedController : public GenericController<T>
{
public:
    using GenericController<T>::GenericController;
    ~BufferedController() override { delete buffer; }

protected:
    bool additionalSetup(hardware_interface::PositionJointInterface* hw, ros::NodeHandle &n, const std::string &description)
    {
        int bufferMinSize;

        if (!n.getParam("buffer_min_size", bufferMinSize) || bufferMinSize <= 0)
        {
            ROS_ERROR("Could not retrieve buffer_min_size or not greater than 0");
            return false;
        }

        buffer = makeBuffer(bufferMinSize);
        return true;
    }

    void onStarting(const std::vector<double> & angles) override
    {
        const auto initialValue = convertToBufferType(angles);
        std::lock_guard<std::mutex> lock(bufferMutex);
        buffer->reset(initialValue);
    }

    void accept(const typename B::ValueType & command, const ros::Time & timestamp)
    {
        const auto steady = ros::SteadyTime(timestamp.toSec());
        std::lock_guard<std::mutex> lock(bufferMutex);
        buffer->accept(command, steady);
    }

    double getCommandPeriod() const
    {
        std::lock_guard<std::mutex> lock(bufferMutex);
        const auto period = buffer->getCommandPeriod();
        return period.toSec();
    }

    virtual B * makeBuffer(int size) = 0;
    virtual typename B::ValueType convertToBufferType(const std::vector<double> & v) = 0;
    virtual std::vector<double> convertToVector(const KDL::JntArray & q, const typename B::ValueType & v, double period) = 0;

private:
    std::vector<double> getDesiredJointValues(const std::vector<double> & current, double period) override final
    {
        std::lock_guard<std::mutex> lock(bufferMutex);
        const auto value = buffer->interpolate();
        return convertToVector(jointVectorToKdl(current), value, period);
    }

    B * buffer {nullptr};
    mutable std::mutex bufferMutex;
};

template <typename T>
class JointBufferController : public BufferedController<T, JointCommandBuffer>
{
public:
    using BufferedController<T, JointCommandBuffer>::BufferedController;

protected:
    JointCommandBuffer * makeBuffer(int size) override
    {
        return new JointCommandBuffer(GenericController<T>::getName(), size, GenericController<T>::numJoints());
    }

    KDL::JntArray convertToBufferType(const std::vector<double> & v) override
    {
        return jointVectorToKdl(v);
    }

    std::vector<double> convertToVector(const KDL::JntArray & q, const KDL::JntArray & v, double period) override
    {
        return kdlToJointVector(v);
    }
};

template <typename T>
class FrameBufferController : public BufferedController<T, FrameCommandBuffer>
{
public:
    using BufferedController<T, FrameCommandBuffer>::BufferedController;

protected:
    FrameCommandBuffer * makeBuffer(int size) override
    {
        return new FrameCommandBuffer(GenericController<T>::getName(), size);
    }
};

template <typename T>
class StepperController : public GenericController<T>
{
public:
    using GenericController<T>::GenericController;

protected:
    bool additionalSetup(hardware_interface::PositionJointInterface* hw, ros::NodeHandle &n, const std::string &description) override
    {
        if (!n.getParam("step", step) || step <= 0.0)
        {
            ROS_ERROR("Could not retrieve step or not greater than 0");
            return false;
        }

        stored.resize(GenericController<T>::numJoints(), 0.0);
        return true;
    }

    void accept(const std::vector<double> & command)
    {
        std::lock_guard<std::mutex> lock(storageMutex);
        stored = command;
    }

private:
    std::vector<double> getDesiredJointValues(const std::vector<double> & current, double period) override final
    {
        std::vector<double> desired(current.size());
        std::lock_guard<std::mutex> lock(storageMutex);
        std::transform(current.cbegin(), current.cend(), stored.cbegin(), desired.begin(),
                       [this](double c, double s) { return c + step * s; });
        return desired;
    }

    double step {0.0};
    std::vector<double> stored;
    mutable std::mutex storageMutex;
};

} // namespace tiago_telepresence_controllers

#endif // __TIAGO_GENERIC_TP_CONTROLLER_HPP__
