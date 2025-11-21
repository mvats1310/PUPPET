// -*- mode:C++; tab-width:4; c-basic-offset:4; indent-tabs-mode:nil -*-

#ifndef __TIAGO_SUBPROBLEMS_HPP__
#define __TIAGO_SUBPROBLEMS_HPP__

#include <kdl/frames.hpp>

#include "ScrewTheoryIkProblem.hpp"
#include "MatrixExponential.hpp"

namespace roboticslab
{

/**
 * @ingroup ScrewTheoryLib
 *
 * @brief First Paden-Kahan subproblem (modified)
 *
 * Single solution, single revolute joint geometric IK subproblem given by
 * @f$ e\,^{\hat{\xi}\,{\theta}} \cdot p = k @f$
 * (rotation screw applied to a point).
 */
class TiagoOne : public ScrewTheoryIkSubproblem
{
public:
    using ScrewTheoryIkSubproblem::solve;

    /**
     * @brief Constructor
     *
     * @param exp POE term.
     * @param p Characteristic point.
     */
    TiagoOne(const MatrixExponential & exp, const KDL::Vector & p, const KDL::Frame & H_ST_0, const KDL::Frame & H_0_N_init, double theta);

    bool solve(const KDL::Frame & rhs, const KDL::Frame & pointTransform, const JointConfig & reference, Solutions & solutions) const override;

    int solutions() const override
    { return 1; }

    const char * describe() const override
    { return "TIAGO1"; }

private:
    const MatrixExponential exp;
    const KDL::Rotation axisPow;
    const KDL::Vector u, u_p;
    const KDL::Frame H_ST_0;
    double initialSolution, offset;
};

/**
 * @ingroup ScrewTheoryLib
 *
 * @brief First Paden-Kahan subproblem
 *
 * Single solution, single revolute joint geometric IK subproblem given by
 * @f$ e\,^{\hat{\xi}\,{\theta}} \cdot p = k @f$
 * (rotation screw applied to a point).
 */
class PadenKahanOne : public ScrewTheoryIkSubproblem
{
public:
    /**
     * @brief Constructor
     *
     * @param exp POE term.
     * @param p Characteristic point.
     */
    PadenKahanOne(const MatrixExponential & exp, const KDL::Vector & p);

    bool solve(const KDL::Frame & rhs, const KDL::Frame & pointTransform, const JointConfig & reference, Solutions & solutions) const override;

    int solutions() const override
    { return 1; }

    const char * describe() const override
    { return "PK1"; }

private:
    const MatrixExponential exp;
    const KDL::Vector p;
    const KDL::Rotation axisPow;
};

/**
 * @ingroup ScrewTheoryLib
 *
 * @brief Second Paden-Kahan subproblem (normal axes)
 *
 * Dual solution, double revolute joint geometric IK subproblem given by
 * @f$ e\,^{\hat{\xi_1}\,{\theta_1}} \cdot e\,^{\hat{\xi_2}\,{\theta_2}} \cdot p = k @f$
 * (consecutive crossing normal rotation screws to a point).
 */
class PadenKahanTwoNormal : public ScrewTheoryIkSubproblem
{
public:
    /**
     * @brief Constructor
     *
     * @param exp1 First POE term.
     * @param exp2 Second POE term.
     * @param p Characteristic point.
     * @param r Point of intersection between both screw axes.
     */
    PadenKahanTwoNormal(const MatrixExponential & exp1, const MatrixExponential & exp2, const KDL::Vector & p, const KDL::Vector & r);

    bool solve(const KDL::Frame & rhs, const KDL::Frame & pointTransform, const JointConfig & reference, Solutions & solutions) const override;

    int solutions() const override
    { return 2; }

    const char * describe() const override
    { return "PK2N"; }

private:
    const MatrixExponential exp1, exp2;
    const KDL::Vector p, r, axesCross;
    const KDL::Rotation axisPow1, axisPow2;
    const double axesDot;
};


/**
 * @ingroup ScrewTheoryLib
 *
 * @brief Third Paden-Kahan subproblem
 *
 * Dual solution, single revolute joint geometric IK subproblem given by
 * @f$ \left \| e\,^{\hat{\xi}\,{\theta}} \cdot p - k \right \| = \delta @f$
 * (rotation screw for moving @f$ p @f$ to a distance @f$ \delta @f$ from @f$ k @f$).
 */
class PadenKahanThree : public ScrewTheoryIkSubproblem
{
public:
    /**
     * @brief Constructor
     *
     * @param exp POE term.
     * @param p First characteristic point.
     * @param k Second characteristic point.
     */
    PadenKahanThree(const MatrixExponential & exp, const KDL::Vector & p, const KDL::Vector & k);

    bool solve(const KDL::Frame & rhs, const KDL::Frame & pointTransform, const JointConfig & reference, Solutions & solutions) const override;

    int solutions() const override
    { return 2; }

    const char * describe() const override
    { return "PK3"; }

private:
    const MatrixExponential exp;
    const KDL::Vector p, k;
    const KDL::Rotation axisPow;
};

} // namespace roboticslab

#endif // __TIAGO_SUBPROBLEMS_HPP__
