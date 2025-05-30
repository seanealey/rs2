#ifndef GUI_H
#define GUI_H

#include <QWidget>
#include <iostream>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QSlider>
#include <QLabel>
#include <QPushButton>
#include <QGroupBox>
#include <QSpinBox>
#include <QDoubleSpinBox>
#include <QFrame>
#include <QKeyEvent>
#include <QApplication>
#include <QFont>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_srvs/srv/set_bool.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>
#include <std_msgs/msg/string.hpp>
#include <mutex>
#include <atomic>
#include <std_srvs/srv/trigger.hpp>



// Forward declarations
class QSlider;
class QLabel;
class QPushButton;
class QFrame;
class QKeyEvent;
class QEvent;

class GUI : public QWidget
{
    Q_OBJECT

public:
    GUI(rclcpp::Node::SharedPtr node, QWidget *parent = nullptr);

protected:
    // Event filter to handle application-wide events
    bool eventFilter(QObject *obj, QEvent *event) override;

//private slots:
    
    
private:
    void toggleEStop();
    void toggleTurn();
//slots?
    void setupUI();
    void updateMasterControlStatus(bool active);
    void updateStatus();

    void turn_callback(const std_msgs::msg::Bool::SharedPtr msg);

    void publishDMSState();  // Function to publish DMS state
    
    // ROS2 node and publisher
    std::shared_ptr<rclcpp::Node> node_;
    std::shared_ptr<rclcpp::Publisher<std_msgs::msg::Bool>> estop_pub_;
    std::shared_ptr<rclcpp::Publisher<std_msgs::msg::Bool>> dms_pub_;
    std::shared_ptr<rclcpp::Publisher<std_msgs::msg::Bool>> turn_pub_;
    std::shared_ptr<rclcpp::Subscription<std_msgs::msg::Bool>> turn_sub_;
    std::shared_ptr<rclcpp::Publisher<std_msgs::msg::String>> diff_pub_;
    rclcpp::Client<std_srvs::srv::Trigger>::SharedPtr start_service_client_;
    

    QLabel *statusLabel;
    
    // E-Stop components
    QPushButton *estopButton;
    QFrame *estopIndicator;
    QLabel *estopLabel;
    bool estopActive;

    
    // Master Control components
    QFrame *masterControlBar;
    QLabel *masterControlLabel;
    bool spacePressed;  // To track spacebar state
    rclcpp::TimerBase::SharedPtr dms_timer_;
    
    // Turn control components
    QPushButton *turnButton;
    QFrame *turnIndicator;
    bool isRobotTurn;

    //Difficulty Slider
    QSlider *difficultySlider;
    QLabel *difficultyLabel;
    int difficulty_;

    //Start button
    QPushButton *startButton;
    bool started_;

    //mutex
    
    std::mutex mtx;
};

#endif // GUI_H