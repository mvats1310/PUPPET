#ifndef __COMMAND_BUFFER_HPP__
#define __COMMAND_BUFFER_HPP__

#include <iterator> // std::advance
#include <list>
#include <memory> // std::unique_ptr
#include <utility> // std::pair
#include <vector>

#include <ros/console.h>
#include <ros/time.h>

#include <kdl/frames.hpp>
#include <kdl/jntarray.hpp>
#include <kdl/trajectory.hpp>

constexpr auto CAPACITY_MULTIPLIER = 5;

template <typename T>
class CommandBufferBase
{
public:
    using ValueType = T;

    CommandBufferBase(const std::string & name, int minSize)
        : name(name), minSize(minSize)
    { }

    virtual ~CommandBufferBase() = default;

    void accept(const T & command, const ros::SteadyTime & timestamp)
    {
        buffer.emplace_back(command, timestamp);

        if (buffer.size() > minSize * (CAPACITY_MULTIPLIER + 1))
        {
            if (left == buffer.begin())
            {
                // undesirable, but we need to keep our iterators valid
                std::advance(left, 1);
                std::advance(right, 1);
                ROS_WARN("[%s] Reached buffer front", name.c_str());
            }

            buffer.pop_front();

            if (!enabled)
            {
                if (left == right)
                {
                    std::advance(right, 1);
                    left->second = right->second;
                }

                update();
                offset = ros::SteadyTime::now() - left->second;
                enabled = true;
            }
        }
    }

    T interpolate()
    {
        const auto refTime = ros::SteadyTime::now() - offset;

        if (enabled && !buffer.empty() && left->second <= refTime)
        {
            bool needsUpdate = false;

            while (right->second < refTime && right != buffer.end())
            {
                std::advance(left, 1);
                std::advance(right, 1);
                needsUpdate = true;
            }

            if (right != buffer.end())
            {
                if (needsUpdate)
                {
                    update();
                }

                const auto t = (refTime - left->second).toSec();
                return interpolateInternal(t);
            }
            else
            {
                ROS_WARN("[%s] Reached buffer rear", name.c_str());
                right = left;
            }
        }

        enabled = false;
        return right->first;
    }

    ros::WallDuration getCommandPeriod() const
    {
        return !buffer.empty() ? (right->second - left->second) : ros::WallDuration(0.0);
    }

    void reset(const T & initialCommand)
    {
        offset.fromSec(0.0);
        buffer.assign(minSize * CAPACITY_MULTIPLIER, std::make_pair(initialCommand, ros::SteadyTime(0.0)));

        left = right = buffer.end();
        std::advance(left, -1);
        std::advance(right, -1);

        enabled = false;

        resetInternal();
    }

protected:
    using BufferType = std::list<std::pair<T, ros::SteadyTime>>;

    virtual void update() = 0;
    virtual T interpolateInternal(double t) = 0;
    virtual void resetInternal() { }

    typename BufferType::iterator left;
    typename BufferType::iterator right;

private:
    const std::string name;
    const int minSize {0};
    BufferType buffer;
    ros::WallDuration offset;
    bool enabled {false};
};

class JointCommandBuffer : public CommandBufferBase<KDL::JntArray>
{
public:
    JointCommandBuffer(const std::string & name, int minSize, int cmdSize)
        : CommandBufferBase(name, minSize),
          slopes(cmdSize, 0.0)
    { }

protected:
    void update() override;
    KDL::JntArray interpolateInternal(double t) override;
    void resetInternal() override;

private:
    std::vector<double> slopes;
};

class FrameCommandBuffer : public CommandBufferBase<KDL::Frame>
{
public:
    using CommandBufferBase::CommandBufferBase;

protected:
    void update() override;
    KDL::Frame interpolateInternal(double t) override;
    void resetInternal() override;

private:
    std::unique_ptr<KDL::Trajectory> trajectory;
};

#endif // __COMMAND_BUFFER_HPP__
