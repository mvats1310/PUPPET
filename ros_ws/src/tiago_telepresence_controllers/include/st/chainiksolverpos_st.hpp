// -*- mode:C++; tab-width:4; c-basic-offset:4; indent-tabs-mode:nil -*-

#ifndef __CHAIN_IK_SOLVER_POS_ST_HPP__
#define __CHAIN_IK_SOLVER_POS_ST_HPP__

#include <memory> // std::unique_ptr

#include <kdl/chainiksolver.hpp>

#include "ScrewTheoryIkProblem.hpp"

class ChainIkSolverPos_ST : public KDL::ChainIkSolverPos
{
public:
    ChainIkSolverPos_ST(const KDL::Chain & chain, const KDL::Frame & H_0_N_init, const KDL::JntArray & q_init);
    int CartToJnt(const KDL::JntArray & q_init, const KDL::Frame & p_in, KDL::JntArray & q_out) override;
    void updateInternalDataStructures() override {}
    const char * strError(int error) const override;

    static constexpr int E_NOT_REACHABLE = 100;

private:
    std::unique_ptr<roboticslab::ScrewTheoryIkProblem> problem;
    const int solutionIndex {-1};
};

#endif // __CHAIN_IK_SOLVER_POS_ST_HPP__
