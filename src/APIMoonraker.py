#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# APIMoonraker.py
#
# HTTP API for Moonraker.

import json
import time
import urllib.parse
import urllib.request
import operator
import socket

class APIMoonraker():
    # TODO are these states correct?
    statesWithWarning = [
        "printing", "pausing", "paused"
    ]

    def __init__(self, parent, host, webcam):
        self.parent = parent
        self.host = host
        self.webcamIndex = webcam

    # return list of tuples ( "name", func(name) )
    # with all available commands.
    # call function with name of action!
    def getAvailableCommands(self):
        commands = []
        self.devices = self.getDeviceList()

        for d in self.devices:
            #for a in [ "Turn on", "Turn off", "Toggle" ]:
            for a in [ "Turn on", "Turn off" ]:
                name = a + " " + d
                cmd = ( name, self.toggleDevice )
                commands.append(cmd)

        return commands

    ############
    # HTTP API #
    ############

    # only used internally
    def sendRequest(self, headers, path, content = None):
        url = "http://" + self.host + "/" + path
        if content == None:
            request = urllib.request.Request(url, None, headers)
        else:
            data = content.encode('ascii')
            request = urllib.request.Request(url, data, headers)

        try:
            with urllib.request.urlopen(request, None, self.parent.networkTimeout) as response:
                text = response.read()
                #print("Klipper Rx: \"" + str(text) + "\"\n")
                return text
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            print("Error requesting URL \"" + url + "\": \"" + str(error) + "\"")
            return "error"
        except socket.timeout:
            print("Timeout waiting for response to \"" + url + "\"")
            return "timeout"

    # only used internally
    def sendPostRequest(self, path, content):
        headers = {
            "Content-Type": "application/json"
        }
        return self.sendRequest(headers, path, content)

    # only used internally
    def sendGetRequest(self, path):
        headers = {}
        return self.sendRequest(headers, path)

    #####################
    # Command discovery #
    #####################

    def getDeviceList(self):
        devices = []

        r = self.sendGetRequest("machine/device_power/devices")
        if (r == "timeout") or (r == "error"):
            return devices

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "devices" in rd["result"]:
                    for d in rd["result"]["devices"]:
                        if "device" in d:
                            devices.append(d["device"])

        except json.JSONDecodeError:
            pass

        return devices

    # return "unknown" when no power can be toggled
    def getMethod(self):
        if len(self.devices) <= 0:
            return "unknown"
        return "moonraker"

    #################
    # Safety Checks #
    #################

    # only used internally
    def stateSafetyCheck(self, actionString):
        state = self.getState()
        if state.lower() in self.statesWithWarning:
            if self.parent.showDialog("OctoTray Warning", "The printer seems to be running currently!", "Do you really want to " + actionString + "?", True, True) == False:
                return True
        return False

    # only used internally
    def tempSafetyCheck(self, actionString):
        if self.getTemperatureIsSafe() == False:
            if self.parent.showDialog("OctoTray Warning", "The printer seems to still be hot!", "Do you really want to " + actionString + "?", True, True) == False:
                return True
        return False

    # only used internally
    def safetyCheck(self, actionString):
        if self.stateSafetyCheck(actionString):
            return True
        if self.tempSafetyCheck(actionString):
            return True
        return False

    ##################
    # Power Toggling #
    ##################

    # only used internally (passed to caller as a pointer)
    def toggleDevice(self, name):
        # name is "Toggle x" or "Turn on x" or "Turn off x"
        action = ""
        if name.startswith("Toggle "):
            action = "toggle"
            name = name[len("Toggle "):]
        elif name.startswith("Turn on "):
            action = "on"
            name = name[len("Turn on "):]
        elif name.startswith("Turn off "):
            action = "off"
            name = name[len("Turn off "):]

        self.sendPostRequest("machine/device_power/device?device=" + name + "&action=" + action, "")

    # should automatically turn on printer, regardless of method
    def turnOn(self):
        if len(self.devices) > 0:
            self.toggleDevice("Turn on " + self.devices[0])

    # should automatically turn off printer, regardless of method
    def turnOff(self):
        if len(self.devices) > 0:
            self.toggleDevice("Turn off " + self.devices[0])

    ######################
    # Status Information #
    ######################

    # only used internally
    def getState(self):
        # just using octoprint compatibility layer
        r = self.sendGetRequest("api/job")
        try:
            rd = json.loads(r)
            if "state" in rd:
                return rd["state"]
        except json.JSONDecodeError:
            pass
        return "Unknown"

    # only used internally
    def getTemperatureIsSafe(self, limit = 50.0):
        self.sendGetRequest("printer/objects/query?extruder=temperature")
        if (r == "timeout") or (r == "error"):
            return files

        temp = 0.0

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "status" in rd["result"]:
                    if "extruder" in rd["result"]["status"]:
                        if "temperature" in rd["result"]["status"]["extruder"]:
                            temp = float(rd["result"]["status"]["extruder"]["temperature"])

        except json.JSONDecodeError:
            pass

        return temp < limit

    # human readable temperatures
    def getTemperatureString(self):
        r = self.sendGetRequest("printer/objects/query?extruder=temperature,target")
        s = "Unknown"

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "status" in rd["result"]:
                    if "extruder" in rd["result"]["status"]:
                        temp = 0.0
                        target = 0.0
                        if "temperature" in rd["result"]["status"]["extruder"]:
                            temp = float(rd["result"]["status"]["extruder"]["temperature"])
                        if "target" in rd["result"]["status"]["extruder"]:
                            target = float(rd["result"]["status"]["extruder"]["target"])
                        s = str(temp) + " / " + str(target)

        except json.JSONDecodeError:
            pass

        return s

    # human readable name (fall back to hostname)
    def getName(self):
        r = self.sendGetRequest("printer/info")
        s = self.host

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "hostname" in rd["result"]:
                    s = rd["result"]["hostname"]

        except json.JSONDecodeError:
            pass

        return s

    # only used internally
    def getProgress(self):
        # just using octoprint compatibility layer
        r = self.sendGetRequest("api/job")
        try:
            rd = json.loads(r)
            if "progress" in rd:
                return rd["progress"]
        except json.JSONDecodeError:
            pass
        return "Unknown"

    # human readable progress
    def getProgressString(self):
        # just using octoprint compatibility layer
        s = ""
        progress = self.getProgress()
        if ("completion" in progress) and ("printTime" in progress) and ("printTimeLeft" in progress) and (progress["completion"] != None) and (progress["printTime"] != None) and (progress["printTimeLeft"] != None):
            s += "%.1f%%" % progress["completion"]
            s += " - runtime "
            s += time.strftime("%H:%M:%S", time.gmtime(progress["printTime"]))
            s += " - "
            s += time.strftime("%H:%M:%S", time.gmtime(progress["printTimeLeft"])) + " left"
        return s

    ###################
    # Printer Actions #
    ###################

    # only used internally
    def sendGCode(self, cmd):
        self.sendPostRequest("printer/gcode/script?script=" + cmd, "")

    # only used internally
    def isPaused(self):
        r = self.sendGetRequest("objects/query?pause_resume")

        p = False

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "status" in rd["result"]:
                    if "pause_resume" in rd["result"]["status"]:
                        if "is_paused" in rd["result"]["status"]["pause_resume"]:
                            p = rd["result"]["status"]["pause_resume"]["is_paused"]

        except json.JSONDecodeError:
            pass

        return bool(p)

    # only used internally
    def isPositioningAbsolute(self):
        r = self.sendGetRequest("printer/objects/query?gcode_move=absolute_coordinates")

        p = True

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "status" in rd["result"]:
                    if "gcode_move" in rd["result"]["status"]:
                        if "absolute_coordinates" in rd["result"]["status"]["gcode_move"]:
                            p = rd["result"]["status"]["gcode_move"]["absolute_coordinates"]

        except json.JSONDecodeError:
            pass

        return bool(p)

    def callHoming(self, axes = "xyz"):
        if self.stateSafetyCheck("home it"):
            return

        # always home in XYZ order
        if "x" in axes:
            self.sendGCode("G28 X")
        if "y" in axes:
            self.sendGCode("G28 Y")
        if "z" in axes:
            self.sendGCode("G28 Z")

    def callMove(self, axis, dist, speed, relative = True):
        if self.stateSafetyCheck("move it"):
            return

        currentlyAbsolute = self.isPositioningAbsolute()

        if currentlyAbsolute and relative:
            # set to relative positioning
            self.sendGCode("G91")

        if (not currentlyAbsolute) and (not relative):
            # set to absolute positioning
            self.sendGCode("G90")

        # do move
        if axis.lower() == "x":
            self.sendGCode("G0 X" + str(dist) + " F" + str(speed))
        elif axis.lower() == "y":
            self.sendGCode("G0 Y" + str(dist) + " F" + str(speed))
        elif axis.lower() == "z":
            self.sendGCode("G0 Z" + str(dist) + " F" + str(speed))

        if currentlyAbsolute and relative:
            # set to absolute positioning
            self.sendGCode("G90")

        if (not currentlyAbsolute) and (not relative):
            # set to relative positioning
            self.sendGCode("G91")

    def callPauseResume(self):
        if self.stateSafetyCheck("pause/resume"):
            return

        if self.isPaused():
            self.sendPostRequest("printer/print/pause", "")
        else:
            self.sendPostRequest("printer/print/resume", "")

    def callJobCancel(self):
        if self.stateSafetyCheck("cancel"):
            return

        self.sendPostRequest("printer/print/cancel")

    def statusDialog(self):
        progress = self.getProgress()
        s = self.getName() + "\n"
        warning = False
        if ("completion" in progress) and ("printTime" in progress) and ("printTimeLeft" in progress) and (progress["completion"] != None) and (progress["printTime"] != None) and (progress["printTimeLeft"] != None):
            s += "%.1f%% Completion\n" % progress["completion"]
            s += "Printing since " + time.strftime("%H:%M:%S", time.gmtime(progress["printTime"])) + "\n"
            s += time.strftime("%H:%M:%S", time.gmtime(progress["printTimeLeft"])) + " left"
        elif ("completion" in progress) and ("printTime" in progress) and ("printTimeLeft" in progress):
            s += "No job is currently running"
        else:
            s += "Could not read printer status!"
            warning = True
        t = self.getTemperatureString()
        if len(t) > 0:
            s += "\n" + t
        self.parent.showDialog("OctoTray Status", s, None, False, warning)

    #################
    # File Handling #
    #################

    def getRecentFiles(self, count):
        files = []

        r = self.sendGetRequest("server/files/directory")
        if (r == "timeout") or (r == "error"):
            return files

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "files" in rd["result"]:
                    for f in rd["result"]["files"]:
                        if "filename" in f and "modified" in f:
                            tmp = (f["filename"], f["modified"])
                            files.append(tmp)

        except json.JSONDecodeError:
            pass

        files.sort(reverse = True, key = lambda x: x[1])
        files = files[:count]
        return [ ( i[0], i[0] ) for i in files ]

    def printFile(self, path):
        self.sendPostRequest("printer/print/start?filename=" + path, "")

    ###############
    # Temperature #
    ###############

    # only used internally
    def setTemperature(self, cmd, temp):
        cmd_str = cmd + " " + str(int(temp))
        self.sendGCode(cmd_str)

    def printerHeatTool(self, temp):
        self.setTemperature("M104", temp)

    def printerHeatBed(self, temp):
        self.setTemperature("M140", temp)

    def printerCooldown(self):
        if self.stateSafetyCheck("cool it down"):
            return

        self.printerHeatTool(0)
        self.printerHeatBed(0)

    ##########
    # Webcam #
    ##########

    def getWebcamURL(self):
        url = ""

        r = self.sendGetRequest("server/webcams/list")
        if (r == "timeout") or (r == "error"):
            return url

        try:
            rd = json.loads(r)
            if "result" in rd:
                if "webcams" in rd["result"]:
                    if len(rd["result"]["webcams"]) > self.webcamIndex:
                        w = rd["result"]["webcams"][self.webcamIndex]
                        if "snapshot_url" in w:
                            url =  w["snapshot_url"]

        except json.JSONDecodeError:
            pass

        # make relative paths absolute
        if url.startswith("/"):
            url = "http://" + self.host + url

        return url
