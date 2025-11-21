// -*- mode:C++; tab-width:4; c-basic-offset:4; indent-tabs-mode:nil -*-

#include "chainiksolverpos_st.hpp"

#include "ConfigurationSelector.hpp"

using namespace roboticslab;

namespace
{
    int findSolutionIndex(ScrewTheoryIkProblem * problem, const KDL::Frame & H_0_N_init, const KDL::JntArray & q_init)
    {
        std::vector<KDL::JntArray> solutions;
        problem->solve(H_0_N_init, q_init, solutions);

        TiagoConfigurationSelector selector;
        selector.configure(solutions);
        selector.findOptimalConfiguration(q_init);

        return selector.getValidSolutionIndex();
    }
}

// -----------------------------------------------------------------------------

ChainIkSolverPos_ST::ChainIkSolverPos_ST(const KDL::Chain & chain, const KDL::Frame & H_0_N_init, const KDL::JntArray & q_init)
    : problem(buildProblem(PoeExpression::fromChain(chain), H_0_N_init, q_init)),
      solutionIndex(findSolutionIndex(problem.get(), H_0_N_init, q_init))
{}

// -----------------------------------------------------------------------------

int ChainIkSolverPos_ST::CartToJnt(const KDL::JntArray & q_init, const KDL::Frame & p_in, KDL::JntArray & q_out)
{
    std::vector<KDL::JntArray> solutions;
    auto reachability = problem->solve(p_in, q_init, solutions);
    q_out = solutions[solutionIndex];

    return (error = reachability[solutionIndex] ? E_NOERROR : E_NOT_REACHABLE);
}

// -----------------------------------------------------------------------------

const char * ChainIkSolverPos_ST::strError(int error) const
{
    switch (error)
    {
    case E_NOT_REACHABLE:
        return "IK solution not reachable";
    default:
        return KDL::SolverI::strError(error);
    }
}

// -----------------------------------------------------------------------------
