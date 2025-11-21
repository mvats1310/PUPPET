// -*- mode:C++; tab-width:4; c-basic-offset:4; indent-tabs-mode:nil -*-

#include "ScrewTheoryIkProblem.hpp"
#include "TiagoSubproblems.hpp"

using namespace roboticslab;

namespace
{
    KDL::Vector findIntersection(const MatrixExponential & exp1, const MatrixExponential & exp2)
    {
        // "Intersection of Two Lines in Three-Space" by Ronald Goldman, University of Waterloo (Waterloo, Ontario, Canada)
        // published in: "Graphic Gems", edited by Andrew S. Glassner, 1 ed., ch. 5, "3D Geometry" (p. 304)
        // referenced in: https://stackoverflow.com/a/565282

        KDL::Vector cross = exp1.getAxis() * exp2.getAxis();
        KDL::Vector diff = exp2.getOrigin() - exp1.getOrigin();

        double den = KDL::pow(cross.Norm(), 2);
        double t = KDL::dot(cross, diff * exp2.getAxis()) / den;
        double s = KDL::dot(cross, diff * exp1.getAxis()) / den;

        KDL::Vector L1 = exp1.getOrigin() + exp1.getAxis() * t;
        KDL::Vector L2 = exp2.getOrigin() + exp2.getAxis() * s;

        assert(KDL::Equal(L1, L2));

        return L1;
    }
}

// -----------------------------------------------------------------------------

ScrewTheoryIkProblem * roboticslab::buildProblem(const PoeExpression & poe, const KDL::Frame & H_0_N_init, const KDL::JntArray & q_init)
{
    const auto & exp1 = poe.exponentialAtJoint(0);
    const auto & exp2 = poe.exponentialAtJoint(1);
    const auto & exp3 = poe.exponentialAtJoint(2);
    const auto & exp4 = poe.exponentialAtJoint(3);
    const auto & exp5 = poe.exponentialAtJoint(4);
    const auto & exp6 = poe.exponentialAtJoint(5);
    const auto & exp7 = poe.exponentialAtJoint(6);

    const auto a = exp1.getOrigin(); // point on axis 1 only
    const auto b = findIntersection(exp2, exp3); // intersection of axes 2 and 3
    const auto d = findIntersection(exp6, exp7); // intersection of axes 5, 6 and 7
    const auto e = exp7.getOrigin() + exp7.getAxis(); // point on axis 7, but not on 6

    ScrewTheoryIkProblem::Steps steps;
    steps.emplace_back(std::vector<int>{0}, new TiagoOne(exp1, d, poe.getTransform(), H_0_N_init, q_init(0)));
    steps.emplace_back(std::vector<int>{3}, new PadenKahanThree(exp4, d, b));
    steps.emplace_back(std::vector<int>{1, 2}, new PadenKahanTwoNormal(exp2, exp3, d, b));
    steps.emplace_back(std::vector<int>{4, 5}, new PadenKahanTwoNormal(exp5, exp6, e, d));
    steps.emplace_back(std::vector<int>{6}, new PadenKahanOne(exp7, a));

    return ScrewTheoryIkProblem::create(poe, steps);
}

// -----------------------------------------------------------------------------
