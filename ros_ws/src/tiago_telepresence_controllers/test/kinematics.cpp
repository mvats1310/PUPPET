#include "gtest/gtest.h"

#include <ros/ros.h>
#include <kdl_parser/kdl_parser.hpp>
#include <kdl/chainfksolverpos_recursive.hpp>

#include "st/chainiksolverpos_st.hpp"
#include "st/ProductOfExponentials.hpp"
#include "ScrewTheoryIkProblem.hpp"

namespace rl = roboticslab;

inline KDL::JntArray jointVectorToKdl(const std::vector<double> & v)
{
    // https://forum.kde.org/viewtopic.php%3Ff=74&t=94839.html#p331301
    KDL::JntArray ret;
    ret.data = Eigen::VectorXd::Map(v.data(), v.size());
    return ret;
}

class KinematicsTest : public ::testing::Test
{
public:
    KinematicsTest()
    {
        std::string description;
        n.getParam("robot_description", description);

        KDL::Tree tree;
        kdl_parser::treeFromString(description, tree);

        std::string start_link, end_link;
        n.getParam("start_link", start_link);
        n.getParam("end_link", end_link);

        tree.getChain(start_link, end_link, chain);
    }

protected:
    void doCheckST(KDL::ChainFkSolverPos & fkSolverPos, const KDL::JntArray & q);
    void doCheckKDL(KDL::ChainFkSolverPos & fkSolverPos, const KDL::JntArray & q);

    ros::NodeHandle n;
    KDL::Chain chain;

    static const double PI;
    static const double PI_2;
    static const double eps;
};

const double KinematicsTest::PI = KDL::PI;
const double KinematicsTest::PI_2 = KDL::PI / 2;
const double KinematicsTest::eps = 1e-4;

void KinematicsTest::doCheckST(KDL::ChainFkSolverPos & fkSolverPos, const KDL::JntArray & q)
{
    KDL::Frame H;
    ASSERT_EQ(fkSolverPos.JntToCart(q, H), KDL::SolverI::E_NOERROR);

    auto * ikProblem = buildProblem(rl::PoeExpression::fromChain(chain), H, q);
    ASSERT_NE(ikProblem, nullptr);

    std::vector<KDL::JntArray> solutions;
    auto reachability = ikProblem->solve(H, q, solutions);
    ASSERT_EQ(solutions.size(), 8);
    ASSERT_EQ(reachability.size(), 8);

    bool match = false;

    for (int i = 0; i < solutions.size(); i++)
    {
        KDL::Frame H_st;
        ASSERT_EQ(fkSolverPos.JntToCart(solutions[i], H_st), KDL::SolverI::E_NOERROR);
        ASSERT_FALSE(reachability[i] ^ KDL::Equal(H, H_st));

        bool test = true;

        for (int j = 0; j < q.rows(); j++)
        {
            // the KDL::Equal overload for JntArray always returns false for some reason
            test &= KDL::Equal(solutions[i](j), q(j));
        }

        match |= test;
    }

    ASSERT_TRUE(match);
}

void KinematicsTest::doCheckKDL(KDL::ChainFkSolverPos & fkSolverPos, const KDL::JntArray & q)
{
    KDL::Frame H;
    ASSERT_EQ(fkSolverPos.JntToCart(q, H), KDL::SolverI::E_NOERROR);

    ChainIkSolverPos_ST ikSolverPos(chain, H, q);
    KDL::JntArray q_st(chain.getNrOfJoints());
    ASSERT_EQ(ikSolverPos.CartToJnt(q, H, q_st), KDL::SolverI::E_NOERROR);

    bool test = true;

    for (int i = 0; i < q.rows(); i++)
    {
        // the KDL::Equal overload for JntArray always returns false for some reason
        test &= KDL::Equal(q(i), q_st(i));
    }

    ASSERT_TRUE(test);
}

TEST_F(KinematicsTest, ScrewTheoryIkProblem_Test)
{
    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    doCheckST(fkSolverPos, jointVectorToKdl(std::vector<double>(7, 0.0)));
    doCheckST(fkSolverPos, jointVectorToKdl(std::vector<double>(7, 0.1)));
    doCheckST(fkSolverPos, jointVectorToKdl(std::vector<double>(7, PI_2)));
    doCheckST(fkSolverPos, jointVectorToKdl(std::vector<double>(7, PI)));
}

TEST_F(KinematicsTest, ChainIkSolverPos_ST_Test)
{
    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    doCheckKDL(fkSolverPos, jointVectorToKdl(std::vector<double>(7, 0.0)));
    doCheckKDL(fkSolverPos, jointVectorToKdl(std::vector<double>(7, 0.1)));
    doCheckKDL(fkSolverPos, jointVectorToKdl(std::vector<double>(7, PI_2)));
    doCheckKDL(fkSolverPos, jointVectorToKdl(std::vector<double>(7, PI)));
}

TEST_F(KinematicsTest, DH_Test)
{
    // from `robot_description`:
    // arm_1_joint:        xyz=" 0.15505  0.014  -0.151"    rpy="0 0 -1.5707963267948966"
    // arm_2_joint:        xyz=" 0.125    0.0195 -0.031"    rpy="1.5707963267948966 0.0 0.0"
    // arm_3_joint:        xyz=" 0.0895   0.0    -0.0015"   rpy="-1.5707963267948966 0.0 1.5707963267948966"
    // arm_4_joint:        xyz="-0.02    -0.027  -0.222"    rpy="-1.5707963267948966 -1.5707963267948966 0.0"
    // arm_5_joint:        xyz="-0.162    0.02    0.027"    rpy="1.5707963267948966 -1.5707963267948966 -1.5707963267948966"
    // arm_6_joint:        xyz=" 0        0       0.15"     rpy="0.0 -1.5707963267948966 -1.5707963267948966"
    // arm_7_joint:        xyz=" 0        0       0"        rpy="1.5707963267948966 0.0 1.5707963267948966"
    // arm_tool_joint:     xyz=" 0        0       0.046"    rpy="1.5707963267948966 -1.5707963267948966 3.141592653589793"
    // wrist_ft_joint:     xyz=" 0.00785  0       0"        rpy="1.5707963267948966 0 1.5707963267948966"
    // wrist_tool_joint:   xyz=" 0        0       0.012725" rpy="-1.5707963267948966 -1.5707963267948966 0"
    // gripper_joint:      xyz=" 0.01     0       0"        rpy="1.5707963267948966 1.5707963267948966 -1.5707963267948966"
    // gripper_base_joint: xyz=" 0.       0       0"        rpy="0 3.1416 1.5707"
    // gripper_grasping_frame_joint: rpy="0 -1.5708 0" xyz="0 0 0.12"

    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    KDL::Frame H;

    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);

    // H_torso_0.p =         [0.15505   0.014    -0.151]
    // H_torso_1.p =         [0.17455  -0.111    -0.182]
    // H_torso_2.p =         [0.17605  -0.2005   -0.182]
    // H_torso_3.p =         [0.14905  -0.4225   -0.202]
    // H_torso_4.p =         [0.17605  -0.5845   -0.182]
    // H_torso_5.p =         [0.17605  -0.7345   -0.182]
    // H_torso_6.p =         [0.17605  -0.7345   -0.182]
    // H_torso_flange.p =    [0.17605  -0.7805   -0.182]
    // H_torso_ft.p =        [0.17605  -0.78835  -0.182]
    // H_torso_ft_flange.p = [0.17605  -0.801075 -0.182]
    // H_torso_gripper.p =   [0.17605  -0.811075 -0.182]
    // H_torso_gripper_b.p = [0.17605  -0.811075 -0.182]
    // H_torso_grasping.p =  [0.176051 -0.931075 -0.182]
    // angle = 2.094449, axis = [0.577370 -0.577368 -0.577312]

    const auto RotZ = KDL::Joint(KDL::Joint::RotZ);
    const auto fixed = KDL::Joint(KDL::Joint::None);

    KDL::Chain chain_dh;

    // H_torso_0
    chain_dh.addSegment(KDL::Segment(fixed, KDL::Frame(KDL::Rotation::RotZ(-PI_2), KDL::Vector(0.15505, 0.014, -0.151))));

    //                                                 KDL::Frame::DH(    A, alpha,       D, theta)
    /* H_0_1 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(0.125,  PI_2,  -0.031,   0.0)));
    /* H_1_2 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0, -PI_2,  -0.021,  PI_2)));
    /* H_2_3 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(-0.02, -PI_2, -0.3115,   0.0)));
    /* H_3_4 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH( 0.02, -PI_2,     0.0,   0.0)));
    /* H_4_5 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0, -PI_2,   0.312, -PI_2)));
    /* H_5_6 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0,  PI_2,     0.0,   0.0)));
    /* H_6_7 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0,   0.0,   0.046,   0.0)));

    // H_7_N
    chain_dh.addSegment(KDL::Segment(fixed, KDL::Frame(KDL::Rotation::RPY(-PI_2, -PI_2, 0.0)))); // `R_z * R_y * R_x` with (x, y, z)

    // H_N_FT
    chain_dh.addSegment(KDL::Segment(fixed, KDL::Frame(KDL::Vector(0.020575, 0.0, 0.0))));

    // H_FT_TCP
    chain_dh.addSegment(KDL::Segment(fixed, KDL::Frame(KDL::Rotation::RotX(PI_2), KDL::Vector(0.13, 0.0, 0.0))));

    KDL::ChainFkSolverPos_recursive fkSolverPos_dh(chain_dh);

    KDL::Frame H_dh;
    ASSERT_TRUE(fkSolverPos_dh.JntToCart(q, H_dh) == KDL::SolverI::E_NOERROR);

    ASSERT_TRUE(KDL::Equal(H, H_dh, eps));

    q = jointVectorToKdl(std::vector<double>(chain.getNrOfJoints(), 0.1));
    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);
    ASSERT_TRUE(fkSolverPos_dh.JntToCart(q, H_dh) == KDL::SolverI::E_NOERROR);

    ASSERT_TRUE(KDL::Equal(H, H_dh, eps));
}

TEST_F(KinematicsTest, ST_Test)
{
    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    KDL::Frame H;

    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);

    KDL::Frame H_ST_0(KDL::Rotation::RPY(PI_2, 0.0, -PI_2), KDL::Vector(0.176051, -0.931075, -0.182));
    rl::PoeExpression poe(H_ST_0);

    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  0, 1}, {0.15505,  0.014,  -0.182}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, {-1,  0, 0}, {0.17605, -0.111,  -0.182}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  1, 0}, {0.17605, -0.111,  -0.182}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 1,  0, 0}, {0.17605, -0.4225, -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0, -1, 0}, {0.17605, -0.7345, -0.182}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  0, 1}, {0.17605, -0.7345, -0.182}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0, -1, 0}, {0.17605, -0.7345, -0.182}));

    KDL::Frame H_ST;
    ASSERT_TRUE(poe.evaluate(q, H_ST));

    ASSERT_TRUE(KDL::Equal(H, H_ST, eps));

    q = jointVectorToKdl(std::vector<double>(chain.getNrOfJoints(), 0.1));
    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);
    ASSERT_TRUE(poe.evaluate(q, H_ST));

    ASSERT_TRUE(KDL::Equal(H, H_ST, eps));
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    ros::init(argc, argv, "kinematics_test");
    return RUN_ALL_TESTS();
}
