#include "gtest/gtest.h"

#include <ros/ros.h>
#include <kdl_parser/kdl_parser.hpp>
#include <kdl/chainfksolverpos_recursive.hpp>

#include "st/chainiksolverpos_st.hpp"
#include "st/ProductOfExponentials.hpp"

namespace rl = roboticslab;

inline KDL::JntArray jointVectorToKdl(const std::vector<double> & v)
{
    // https://forum.kde.org/viewtopic.php%3Ff=74&t=94839.html#p331301
    KDL::JntArray ret;
    ret.data = Eigen::VectorXd::Map(v.data(), v.size());
    return ret;
}

class KinematicsDualTest : public ::testing::Test
{
public:
    KinematicsDualTest()
    {
        std::string description;
        n.getParam("robot_description", description);

        kdl_parser::treeFromString(description, tree);
    }

protected:
    void doCheck(const KDL::Chain & chain, KDL::ChainFkSolverPos & fkSolverPos, const KDL::JntArray & q);

    ros::NodeHandle n;
    KDL::Tree tree;

    static const double PI;
    static const double PI_2;
    static const double eps;
};

const double KinematicsDualTest::PI = KDL::PI;
const double KinematicsDualTest::PI_2 = KDL::PI / 2;
const double KinematicsDualTest::eps = 1e-4;

void KinematicsDualTest::doCheck(const KDL::Chain & chain, KDL::ChainFkSolverPos & fkSolverPos, const KDL::JntArray & q)
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

TEST_F(KinematicsDualTest, ChainIkSolverPos_ST_Test)
{
    KDL::Chain chain;
    ASSERT_TRUE(tree.getChain("torso_lift_link", "gripper_right_grasping_frame", chain));

    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    doCheck(chain, fkSolverPos, jointVectorToKdl(std::vector<double>(7, 0.0)));
    doCheck(chain, fkSolverPos, jointVectorToKdl(std::vector<double>(7, 0.1)));
    doCheck(chain, fkSolverPos, jointVectorToKdl(std::vector<double>(7, PI_2)));
    doCheck(chain, fkSolverPos, jointVectorToKdl(std::vector<double>(7, PI)));
}

TEST_F(KinematicsDualTest, DH_RightArm_Test)
{
    KDL::Chain chain;
    ASSERT_TRUE(tree.getChain("torso_lift_link", "gripper_right_grasping_frame", chain));

    // from `robot_description`:
    // arm_right_1_joint:        xyz=" 0.02556 -0.19   -0.171"    rpy="0 0 -1.5707963267948966"
    // arm_right_2_joint:        xyz=" 0.125   -0.0195 -0.031"    rpy="-1.5707963267948966 0.0 0.0"
    // arm_right_3_joint:        xyz=" 0.0895   0.0    -0.0015"   rpy="-1.5707963267948966 0.0 1.5707963267948966"
    // arm_right_4_joint:        xyz="-0.02    -0.027  -0.222"    rpy="-1.5707963267948966 -1.5707963267948966 0.0"
    // arm_right_5_joint:        xyz="-0.162    0.02    0.027"    rpy="1.5707963267948966 -1.5707963267948966 -1.5707963267948966"
    // arm_right_6_joint:        xyz=" 0        0       0.15"     rpy="0.0 -1.5707963267948966 -1.5707963267948966"
    // arm_right_7_joint:        xyz=" 0        0       0"        rpy="1.5707963267948966 0.0 1.5707963267948966"
    // arm_right_tool_joint:     xyz=" 0        0       0.046"    rpy="1.5707963267948966 -1.5707963267948966 3.141592653589793"
    // wrist_right_ft_joint:     xyz=" 0.00785  0       0"        rpy="1.5707963267948966 0 1.5707963267948966"
    // wrist_right_tool_joint:   xyz=" 0        0       0.012725" rpy="-1.5707963267948966 -1.5707963267948966 0"
    // gripper_right_joint:      xyz=" 0.01     0       0"        rpy="1.5707963267948966 1.5707963267948966 -1.5707963267948966"
    // gripper_right_base_joint: xyz=" 0.       0       0"        rpy="0 3.1416 1.5707"
    // gripper_right_grasping_frame_joint: rpy="0 -1.5708 0" xyz="0 0 0.12"

    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    KDL::Frame H;

    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);

    // H_torso_0.p =         [0.02556  -0.190    -0.171]
    // H_torso_1.p =         [0.00606  -0.315    -0.202]
    // H_torso_2.p =         [0.00456  -0.4045   -0.202]
    // H_torso_3.p =         [0.03156  -0.6265   -0.182]
    // H_torso_4.p =         [0.00456  -0.7885   -0.202]
    // H_torso_5.p =         [0.00456  -0.9385   -0.202]
    // H_torso_6.p =         [0.00456  -0.9385   -0.202]
    // H_torso_7.p =         [0.00456  -0.98450  -0.202]
    // H_torso_ft.p =        [0.00456  -0.99235  -0.202]
    // H_torso_ft_N.p =      [0.00456  -1.005075 -0.202]
    // H_torso_gripper.p =   [0.00456  -1.015075 -0.202]
    // H_torso_gripper_b.p = [0.00456  -1.015075 -0.202]
    // H_torso_grasping.p =  [0.004559 -1.135075 -0.202]
    // angle = 2.094342, axis = [-0.577330 0.577332 -0.577388]

    const auto RotZ = KDL::Joint(KDL::Joint::RotZ);
    const auto fixed = KDL::Joint(KDL::Joint::None);

    KDL::Chain chain_dh;

    // H_torso_0
    chain_dh.addSegment(KDL::Segment(fixed, KDL::Frame(KDL::Rotation::RotZ(-PI_2), KDL::Vector(0.02556, -0.19, -0.171))));

    //                                                 KDL::Frame::DH(    A, alpha,       D, theta)
    /* H_0_1 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(0.125, -PI_2,  -0.031,   0.0)));
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

TEST_F(KinematicsDualTest, DH_LeftArm_Test)
{
    KDL::Chain chain;
    ASSERT_TRUE(tree.getChain("torso_lift_link", "gripper_left_grasping_frame", chain));

    // from `robot_description`:
    // arm_left_1_joint:        xyz=" 0.02556 0.19   -0.171"    rpy="3.141592653589793 0 1.5707963267948966"
    // arm_left_2_joint:        xyz=" 0.125  -0.0195  0.031"    rpy="1.5707963267948966 0.0 0.0"
    // arm_left_3_joint:        xyz=" 0.0895  0.0    -0.0015"   rpy="-1.5707963267948966 3.141592653589793 -1.5707963267948966"
    // arm_left_4_joint:        xyz="-0.02   -0.027   0.222"    rpy="1.5707963267948966 -1.5707963267948966 0.0"
    // arm_left_5_joint:        xyz=" 0.162  -0.02   -0.027"    rpy="1.5707963267948966 -1.5707963267948966 -1.5707963267948966"
    // arm_left_6_joint:        xyz=" 0       0      -0.15"     rpy="0.0 -1.5707963267948966 -1.5707963267948966"
    // arm_left_7_joint:        xyz=" 0       0       0"        rpy="1.5707963267948966 0.0 1.5707963267948966"
    // arm_left_tool_joint:     xyz=" 0       0      -0.046"    rpy="1.5707963267948966 1.5707963267948966 3.141592653589793"
    // wrist_left_ft_joint:     xyz=" 0.00785 0       0"        rpy="1.5707963267948966 0 1.5707963267948966"
    // wrist_left_tool_joint:   xyz=" 0       0       0.012725" rpy="-1.5707963267948966 -1.5707963267948966 0"
    // gripper_left_joint:      xyz=" 0.01    0       0"        rpy="1.5707963267948966 1.5707963267948966 -1.5707963267948966"
    // gripper_left_base_joint: xyz=" 0.      0       0"        rpy="0 3.1416 1.5707"
    // gripper_left_grasping_frame_joint: rpy="0 -1.5708 0" xyz="0 0 0.12"

    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    KDL::Frame H;

    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);

    // H_torso_0.p =         [0.02556  0.19     -0.171]
    // H_torso_1.p =         [0.00606  0.315    -0.202]
    // H_torso_2.p =         [0.00756  0.4045   -0.202]
    // H_torso_3.p =         [0.03456  0.6265   -0.182]
    // H_torso_4.p =         [0.00756  0.7885   -0.202]
    // H_torso_5.p =         [0.00756  0.9385   -0.202]
    // H_torso_6.p =         [0.00756  0.9385   -0.202]
    // H_torso_7.p =         [0.00756  0.9845   -0.202]
    // H_torso_ft.p =        [0.00756  0.99235  -0.202]
    // H_torso_ft_N.p =      [0.00756  1.005075 -0.202]
    // H_torso_gripper.p =   [0.00756  1.015075 -0.202]
    // H_torso_gripper_b.p = [0.00756  1.015075 -0.202]
    // H_torso_grasping.p =  [0.007559 1.135075 -0.202]
    // angle = 2.094453, axis = [0.577367 0.577370 0.577314]

    const auto RotZ = KDL::Joint(KDL::Joint::RotZ);
    const auto fixed = KDL::Joint(KDL::Joint::None);

    KDL::Chain chain_dh;

    // H_torso_0
    chain_dh.addSegment(KDL::Segment(fixed, KDL::Frame(KDL::Rotation::RPY(PI, 0.0, PI_2), KDL::Vector(0.02556, 0.19, -0.171))));

    //                                                 KDL::Frame::DH(    A, alpha,      D, theta)
    /* H_0_1 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(0.125,  PI_2,  0.031,   0.0)));
    /* H_1_2 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0,  PI_2,  0.018,  PI_2)));
    /* H_2_3 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(-0.02,  PI_2, 0.3115,   0.0)));
    /* H_3_4 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH( 0.02,  PI_2,    0.0,   0.0)));
    /* H_4_5 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0,  PI_2, -0.312, -PI_2)));
    /* H_5_6 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0, -PI_2,    0.0,   0.0)));
    /* H_6_7 */ chain_dh.addSegment(KDL::Segment(RotZ, KDL::Frame::DH(  0.0,   0.0, -0.046,   0.0)));

    // H_7_N
    chain_dh.addSegment(KDL::Segment(fixed, KDL::Frame(KDL::Rotation::RPY(PI_2, PI_2, 0.0)))); // `R_z * R_y * R_x` with (x, y, z)

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

TEST_F(KinematicsDualTest, ST_RightArm_Test)
{
    KDL::Chain chain;
    ASSERT_TRUE(tree.getChain("torso_lift_link", "gripper_right_grasping_frame", chain));

    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    KDL::Frame H;

    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);

    KDL::Frame H_ST_0(KDL::Rotation::RPY(-PI_2, 0.0, -PI_2), KDL::Vector(0.00456, -1.135075, -0.202));
    rl::PoeExpression poe(H_ST_0);

    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  0,  1}, {0.02556, -0.19,   -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 1,  0,  0}, {0.00456, -0.315,  -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  1,  0}, {0.00456, -0.315,  -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, {-1,  0,  0}, {0.00456, -0.6265, -0.182}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0, -1,  0}, {0.00456, -0.9385, -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  0, -1}, {0.00456, -0.9385, -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0, -1,  0}, {0.00456, -0.9385, -0.202}));

    KDL::Frame H_ST;
    ASSERT_TRUE(poe.evaluate(q, H_ST));

    ASSERT_TRUE(KDL::Equal(H, H_ST, eps));

    q = jointVectorToKdl(std::vector<double>(chain.getNrOfJoints(), 0.1));
    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);
    ASSERT_TRUE(poe.evaluate(q, H_ST));

    ASSERT_TRUE(KDL::Equal(H, H_ST, eps));
}

TEST_F(KinematicsDualTest, ST_LeftArm_Test)
{
    KDL::Chain chain;
    ASSERT_TRUE(tree.getChain("torso_lift_link", "gripper_left_grasping_frame", chain));

    KDL::ChainFkSolverPos_recursive fkSolverPos(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    KDL::Frame H;

    ASSERT_TRUE(fkSolverPos.JntToCart(q, H) == KDL::SolverI::E_NOERROR);

    KDL::Frame H_ST_0(KDL::Rotation::RPY(PI_2, 0.0, PI_2), KDL::Vector(0.007559, 1.135075, -0.202));
    rl::PoeExpression poe(H_ST_0);

    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  0, -1}, {0.02556,  0.19,   -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, {-1,  0,  0}, {0.007559, 0.315,  -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  1,  0}, {0.007559, 0.315,  -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 1,  0,  0}, {0.007559, 0.6265, -0.182}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0, -1,  0}, {0.007559, 0.9385, -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0,  0,  1}, {0.007559, 0.9385, -0.202}));
    poe.append(rl::MatrixExponential(rl::MatrixExponential::ROTATION, { 0, -1,  0}, {0.007559, 0.9385, -0.202}));

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
    ros::init(argc, argv, "kinematics_dual_test");
    return RUN_ALL_TESTS();
}
