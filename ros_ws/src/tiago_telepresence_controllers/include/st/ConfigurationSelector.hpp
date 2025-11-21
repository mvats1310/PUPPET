// -*- mode:C++; tab-width:4; c-basic-offset:4; indent-tabs-mode:nil -*-

#ifndef __CONFIGURATION_SELECTOR_HPP__
#define __CONFIGURATION_SELECTOR_HPP__

#include <vector>

#include <kdl/frames.hpp>
#include <kdl/jntarray.hpp>
#include <kdl/utilities/utility.h>

namespace roboticslab
{

/**
 * @ingroup ScrewTheoryLib
 *
 * @brief Abstract base class for a robot configuration strategy selector
 */
class ConfigurationSelector
{
public:
    /**
     * @brief Constructor (default)
     */
    ConfigurationSelector() = default;

    /**
     * @brief Constructor
     *
     * @param qMin Joint array of minimum joint limits.
     * @param qMax Joint array of maximum joint limits.
     */
    ConfigurationSelector(const KDL::JntArray & qMin, const KDL::JntArray & qMax)
        : _qMin(qMin),
          _qMax(qMax)
    {}

    //! @brief Destructor
    virtual ~ConfigurationSelector() = default;

    /**
     * @brief Stores initial values for a specific pose.
     *
     * @param solutions Vector of joint arrays that represent all available
     * (valid or not) robot joint poses.
     *
     * @return True/false on success/failure.
     */
    virtual bool configure(const std::vector<KDL::JntArray> & solutions);

    /**
     * @brief Analyzes available configurations and selects the optimal one.
     *
     * @param qGuess Joint array of values for current robot position.
     *
     * @return True/false on success/failure.
     */
    virtual bool findOptimalConfiguration(const KDL::JntArray & qGuess) = 0;

    /**
     * @brief Queries computed joint values for the optimal configuration.
     *
     * @param q Output joint array.
     */
    virtual void retrievePose(KDL::JntArray & q) const
    {
        q = *configs[lastValid].retrievePose();
    }

    /**
     * @brief Retrieves the index of the last valid solution.
     *
     * @return Index of the last valid solution.
     */
    int getValidSolutionIndex() const
    { return lastValid; }

    static constexpr int INVALID_CONFIG = -1;

protected:
    /**
     * @brief Helper class to store a specific robot configuration.
     */
    class Configuration
    {
    public:
        //! @brief Initialize joint values.
        void store(const KDL::JntArray * q)
        { this->q = q; }

        //! @brief Retrieve stored joint values.
        const KDL::JntArray * retrievePose() const
        { return q; }

        //! @brief Whether this configuration is attainable or not.
        bool isValid() const
        { return valid; }

        //! @brief Mark this configuration as invalid.
        void invalidate()
        { valid = false; }

    private:
        const KDL::JntArray * q {nullptr};
        bool valid {true};
    };

    /**
     * @brief Validates a specific robot configuration.
     *
     * @param config Configuration to validate.
     *
     * @return True/false on valid/invalid.
     */
    virtual bool validate(Configuration & config);

    /**
     * @brief Checks if a joint value is within its limits.
     *
     * @param q Joint value.
     * @param qMin Minimum joint limit.
     * @param qMax Maximum joint limit.
     *
     * @return True/false on within/without limits.
     */
    static bool checkJointInLimits(double q, double qMin, double qMax)
    {
        return q >= (qMin - KDL::epsilon) && q <= (qMax + KDL::epsilon);
    }

    KDL::JntArray _qMin, _qMax;

    std::vector<Configuration> configs;
    int lastValid {INVALID_CONFIG};
};

/**
 * @ingroup ScrewTheoryLib
 *
 * @brief IK solver configuration strategy selector based on the overall
 * displacement of all joints.
 *
 * Selects the configuration that entails the lowest sum of displacements
 * across all joints. Works best for all revolute/all prismatic chain types.
 * If attainable, it retains the previous configuration after the first
 * successful choice and discards all other configs for the rest of the
 * instance's lifetime.
 */
class TiagoConfigurationSelector : public ConfigurationSelector
{
public:
    bool findOptimalConfiguration(const KDL::JntArray & qGuess) override;

protected:
    //! @brief Obtains vector of differences between current and desired joint values.
    std::vector<double> getDiffs(const KDL::JntArray & qGuess, const Configuration & config);

    bool validate(Configuration & config) override
    { return true; }
};

} // namespace roboticslab

#endif // __CONFIGURATION_SELECTOR_HPP__
