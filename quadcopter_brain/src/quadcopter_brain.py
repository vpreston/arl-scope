#!/usr/bin/env python

import time
import json
import math
import os

import rospkg
import rospy
import rosbag
import roscopter
import roscopter.msg
import roscopter.srv
from std_srvs.srv import *
from sensor_msgs.msg import NavSatFix, NavSatStatus, Imu
from geodesy import utm


class QuadcopterBrain(object):
    '''
    High-level quadcopter controller.
    '''
    def __init__(self):
        self.clear_waypoints_service = rospy.ServiceProxy(
            'clear_waypoints', Empty)
        self.command_service = rospy.ServiceProxy(
            'command', roscopter.srv.APMCommand)
        self.waypoint_service = rospy.ServiceProxy(
            'waypoint', roscopter.srv.SendWaypoint)
        self.trigger_auto_service = rospy.ServiceProxy(
            'trigger_auto', Empty)
        self.adjust_throttle_service = rospy.ServiceProxy(
            'adjust_throttle', Empty)

    def arm(self):
        self.command_service(roscopter.srv.APMCommandRequest.CMD_ARM)
        print('Armed')

    def launch(self):
        self.command_service(roscopter.srv.APMCommandRequest.CMD_LAUNCH)
        print('Launched')
        time.sleep(5)

    def send_waypoints(self, waypoint_data):
        waypoints = [build_waypoint(datum) for datum in waypoint_data]

        self.trigger_auto_service()
        self.adjust_throttle_service()
        for waypoint in waypoints:
            self.go_to_waypoint(waypoint)

    def land(self):
        self.command_service(roscopter.srv.APMCommandRequest.CMD_LAND)
        print('Landing')

    def go_to_waypoint(self, waypoint):
        successfully_sent_waypoint = False
        tries = 0

        while not successfully_sent_waypoint and tries < 5:
            res = self.waypoint_service(waypoint)
            successfully_sent_waypoint = res.result
            tries += 1
            if successfully_sent_waypoint:
                print('Sent waypoint %d, %d' % (waypoint.latitude,
                                                waypoint.longitude))
                print self.check_reached_waypoint(waypoint)
            else:
                print("Failed to send waypoint %d, %d" % (waypoint.latitude,
                                                          waypoint.longitude))
                time.sleep(0.1)
                if tries == 5:
                    print("Tried % times and giving up" % (tries)) 
                else:
                    print("Retrying. Tries: %d" % (tries))

    def check_reached_waypoint(self, waypoint):
        wait_time = 0
        rospy.Subscriber("/filtered_pos", roscopter.msg.FilteredPosition,
                         self.position_callback)
        while not self.has_reached_waypoint(waypoint) and wait_time < 50:
            time.sleep(5)
            wait_time += 5
            print "--> Traveling to waypoint for %d seconds" % (wait_time)
            print "--> Current position is %d, %d" % (self.current_lat,
                                                          self.current_long)
        if wait_time < 50: # successfully reached
            time.sleep(5) # stay at waypoint for a few seconds
            return "Reached waypoint"
        else:
            return "Failed to reach waypoint" 

    def has_reached_waypoint(self, waypoint):
        error_margin = 3  # in meters
        try:
            current_pt = utm.fromLatLong(self.current_lat, self.current_long)
            current_x = current_pt.easting
            current_y = current_pt.northing
            waypoint_pt = utm.fromLatLong(waypoint.latitude/1e7,
                                          waypoint.longitude/1e7)
            waypoint_x = waypoint_pt.easting
            waypoint_y = waypoint_pt.northing
            x_delta = math.fabs(current_x - waypoint_x)
            y_delta = math.fabs(current_y - waypoint_y)
            dist_from_waypoint = math.sqrt(x_delta**2 + y_delta**2) 
            return dist_from_waypoint < error_margin
        except AttributeError: # if haven't gotten current position data
            return False

    def position_callback(self, data):
        self.current_lat = data.latitude
        self.current_long = data.longitude
        self.current_rel_alt = data.relative_altitude 
        self.current_alt = data.altitude

    def fly_path(self, waypoint_data):
        #self.arm()
        self.launch()
        self.send_waypoints(waypoint_data)
        self.land


def build_waypoint(data):
    latitude = data['latitude']
    longitude = data['longitude']
    altitude = data.get('altitude', 8)
    hold_time = data.get('hold_time', 3.0)

    waypoint = roscopter.msg.Waypoint()
    waypoint.latitude = gps_to_mavlink(latitude)
    waypoint.longitude = gps_to_mavlink(longitude)
    waypoint.altitude = int(altitude * 1000)
    waypoint.hold_time = int(hold_time * 1000)  # in ms
    waypoint.waypoint_type = roscopter.msg.Waypoint.TYPE_NAV
    return waypoint


def gps_to_mavlink(coordinate):
    '''
    coordinate: decimal degrees
    '''
    return int(coordinate * 1e+7)


def open_waypoint_file(filename):
    f = open(filename)
    waypoints = json.load(f)
    rospack = rospkg.RosPack()
    quadcopter_brain_path = rospack.get_path("quadcopter_brain")
    source_path = "src"
    file_path = os.path.join(quadcopter_brain_path, source_path, filename)
    with open(file_path, "r") as f:
        waypoints = json.load(f)
    return waypoints


def main():
    rospy.init_node("quadcopter_brain")
    carl = QuadcopterBrain()
    carl.clear_waypoints_service()
    great_lawn_waypoints = open_waypoint_file(
        "waypoint_data/great_lawn_waypoints.json")
    carl.fly_path([great_lawn_waypoints["A"], great_lawn_waypoints["B"]])


if __name__ == '__main__':
    main()
