#!/usr/bin/env python
import rospy
from std_msgs.msg import *
from std_srvs.srv import Empty
from sensor_msgs.msg import *
from geometry_msgs.msg import TwistStamped
from mavros.msg import *
from mavros.srv import *

class Quadcopter(object):
    def __init__(self):
        self.SUBSCRIBE_TIMEOUT = 2.0
 
        # Subscribe to necessary topics
        self.latest_longitude = -1.0
        self.latest_latitude = -1.0
        topic = '/mavros/fix'
        rospy.Subscriber(topic, NavSatFix, self.gps_callback)
        rospy.loginfo('Just subscribed to %s', topic)
        subscribe_timer = 0.0
        while (self.latest_longitude == -1 or self.latest_latitude == -1) and\
              subscribe_timer < self.SUBSCRIBE_TIMEOUT:
            rospy.sleep(0.1)
            subscribe_timer += 0.1
        if not did_subscribe_succeed(subscribe_timer,
                                     self.SUBSCRIBE_TIMEOUT,
                                     topic):
            # TODO: decide what the right thing to do if subscription fails
            pass

        # Create necessary publishers
        self.rc_override_pub = rospy.Publisher('/mavros/rc/override',
                                               OverrideRCIn, queue_size=10)

        # Create necessary service proxies
        self.launcher = subscribe_service('/mavros/cmd/takeoff', CommandTOL)
        self.arm = subscribe_service('/mavros/cmd/arming', CommandBool)
        self.goto_wp = subscribe_service('/mavros/mission/push', WaypointPush)
        self.lander = subscribe_service('/mavros/cmd/land', CommandTOL)

    def send_rc(self, channels):
        header = Header(seq=1, stamp=rospy.Time.now(), frame_id='')
        rssi = 0
        rospy.loginfo('Trying to send RC signal!')

        channel_msg = OverrideRCIn(channels=channels)
        try:
            self.rc_override_pub.publish(channel_msg.channels)
        except rospy.ServiceException, e:
            return False
            rospy.logwarn('Error encountered in send_rc: %s', str(e))
        rospy.loginfo('Ran send_rc')

    def launch(self, min_pitch = 0.0, yaw = 0.0, altitude = 5.0):
        try:
            res = self.launcher(min_pitch, yaw, self.latest_longitude,
                                self.latest_latitude, altitude)
            print res
            return res.success
        except rospy.ServiceException, e:
            rospy.logwarn('Error encountered in launch: %s', str(e))
            return False
        rospy.loginfo('Ran launch')

    def goto(self, latitude, longitude, altitude = 5.0, is_current = False,
             autocontinue = True, frame = Waypoint.FRAME_GLOBAL,
             cmd = Waypoint.NAV_WAYPOINT):
        wp = Waypoint(frame = frame, command = cmd,
                      is_current = is_current, autocontinue = autocontinue,
                      x_lat = latitude, y_long = longitude, z_alt = altitude)
        try:
            res = self.goto_wp(WaypointPushRequest([wp]))
            return res.success
        except rospy.ServiceException, e:
            rospy.logwarn('Error encountered in goto: %s', str(e))
            return False
        rospy.loginfo('Ran goto')

    def land(self, min_pitch = 0, yaw = 0, altitude = 4):
        try:
            res = self.lander(min_pitch, yaw, self.latest_longitude,
                              self.latest_latitude, altitude)
            print res
            return res.success
        except rospy.ServiceException, e:
            rospy.logwarn('Error encountered in land: %s', str(e))
            return False
        rospy.loginfo('Ran land')

    def gps_callback(self, msg):
        self.latest_longitude = msg.longitude
        self.latest_latitude  = msg.latitude


def did_subscribe_succeed(timer, timeout, topic):
    if timer >= timeout:
        rospy.logwarn("Quadcopter FAILED to subscribe to topic %s", topic)
        return False
    else:
        rospy.loginfo("Quadcopter successfully subscribed to topic %s", topic)
        return True

def annotated_timer(wait_time = 10.0):
    """ Waits for a certain amount of time and prints out updates as it does so.
    Intended to make testing easier so we can time things. Time in seconds"""
    sleep_unit = 5.0
    timer = 0.0
    rospy.loginfo('Waiting for 0.0/%.1f seconds', wait_time)
    while not rospy.is_shutdown() and timer < wait_time:
        rospy.sleep(sleep_unit)
        timer += sleep_unit
        rospy.loginfo('Waiting for %.1f/%.1f seconds', timer, wait_time)
    rospy.loginfo("Done waiting! Do a thing!")
    rospy.sleep(0.1)
    return

def subscribe_service(name, datatype):
    rospy.loginfo('Waiting for service %s...', name)
    rospy.wait_for_service(name)
    rospy.loginfo('\tSuccesfully found service %s', name)
    return rospy.ServiceProxy(name, datatype)


if __name__ == '__main__':
    rospy.init_node('Quadcopter')
    rospy.sleep(1.0)
    quad = Quadcopter()
    rospy.sleep(1.0)

    ###### RC TEST ######
    # channels = [1480, 1500, 1500, 1500, 1430, 1530, 1530, 1500]
    # quad.send_rc(channels)
    #rospy.spin()
    # Tests to run
        # Can we control the gimbal this way like we did in roscopter?
        # Do we need to be in AUTO mode to control the gimbal?
        # Can we command the quadcopter with RC commands?
        # If we control the quadcopter with RC commands, are they done in LOITER
        #   mode or some other mode?

    ###### ARM TEST ######
    # TODO: Arming isnot 
    # if quad.arm(True):
    #     rospy.loginfo("Ran arm successfully!")
    # else:
    #     rospy.logwarn("Failed to arm")    
    # annotated_timer(15)

    ##### LAUNCH TEST ######
    # if quad.launch():
    #     rospy.loginfo("Ran launch successfully!")
    # else:
    #     rospy.logwarn("Failed to launch")
    # Tests to run:
        # Should we try different units for launch altitude?

    ###### WAYPOINT TEST ######
    # Check the position with this: http://www.gps-coordinates.net/
    # This waypoint should be right in front of EH, center of the great lawn
    lat1 = 42.2935566
    lon1 = -71.2652217
    # annotated_timer(15)
    rospy.loginfo("Sending test waypoints...")
    if quad.goto(lat1, lon1, is_current=True):
        rospy.loginfo("Ran goto successfully!")
    else:
        rospy.logwarn("Failed to run goto")
    # Tests to run:
        #   what happens if we don't do autocontinue?
        #   what happens if we set multiple waypoints and then set current wp to
        #       various things? Could we repeat waypoints?
        #   What happens if we change the frame? Go here for more options:
        #       https://github.com/mavlink/mavros/blob/master/mavros/msg/Waypoint.msg
        #       THIS COULD BE SUPER IMPORTANT FOR DOING FIDUCIALS - COULD WE DO
        #       A LOCAL FRAME?
        #   Does the service call return right away, or does it return on completion?

    ###### LAND TEST ######
    # annotated_timer(30)
    # if quad.land():
    #     rospy.loginfo("Ran land successfully!")
    # else:
    #     rospy.logwarn("Failed to land")
    # Tests to run:
        # After running this, do we have RC control?

    rospy.spin()
