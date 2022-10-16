#!/usr/bin/env python3

# OctoTray Linux Qt System Tray OctoPrint client
#
# APIOctoprint.py
#
# HTTP API for OctoPrint.

import json
import time
import urllib.parse
import urllib.request
import operator
import socket

class APIOctoprint():
    statesWithWarning = [
        "printing", "pausing", "paused"
    ]

    def __init__(self, parent, host, key):
        self.parent = parent
        self.host = host
        self.key = key

    # return list of tuples ( "name", func(name) )
    # with all available commands.
    # call function with name of action!
    def getAvailableCommands(self):
        self.method = self.getMethodInternal()
        print("OctoPrint " + self.host + " has method " + self.method)

        commands = []

        if self.method == "unknown":
            # nothing available
            return commands

        # always add available system commands
        systemCommands = self.getSystemCommands()
        for sc in systemCommands:
            commands.append((sc, self.callSystemCommand))

        if self.method == "psucontrol":
            # support for psucontrol plugin
            commands.append(("Turn On PSU", self.setPower))
            commands.append(("Turn Off PSU", self.setPower))

        return commands

    ############
    # HTTP API #
    ############

    # only used internally
    def sendRequest(self, headers, path, content = None):
        url = "http://" + self.host + "/api/" + path
        if content == None:
            request = urllib.request.Request(url, None, headers)
        else:
            data = content.encode('ascii')
            request = urllib.request.Request(url, data, headers)

        try:
            with urllib.request.urlopen(request, None, self.parent.networkTimeout) as response:
                text = response.read()
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
            "Content-Type": "application/json",
            "X-Api-Key": self.key
        }
        return self.sendRequest(headers, path, content)

    # only used internally
    def sendGetRequest(self, path):
        headers = {
            "X-Api-Key": self.key
        }
        return self.sendRequest(headers, path)

    #####################
    # Command discovery #
    #####################

    # only used internally
    def getMethodInternal(self):
        r = self.sendGetRequest("plugin/psucontrol")
        if (r != "timeout") and (r != "error"):
            try:
                rd = json.loads(r)
                if "isPSUOn" in rd:
                    return "psucontrol"
            except json.JSONDecodeError:
                pass

        r = self.sendGetRequest("system/commands/custom")
        if (r == "timeout") or (r == "error"):
            return "unknown"

        try:
            rd = json.loads(r)
            for c in rd:
                if "action" in c:
                    # we have some custom commands and no psucontrol
                    # so lets try to use that instead of skipping
                    # the printer completely with 'unknown'
                    return "system"
        except json.JSONDecodeError:
            pass

        return "unknown"

    # return "unknown" when no power can be toggled
    def getMethod(self):
        return self.method

    # only used internally
    def getSystemCommands(self):
        l = []
        r = self.sendGetRequest("system/commands/custom")
        try:
            rd = json.loads(r)

            if len(rd) > 0:
                print("system commands available for " + self.host + ":")

            for c in rd:
                if "action" in c:
                    print("  - " + c["action"])
                    l.append(c["action"])
        except json.JSONDecodeError:
            pass
        return l

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
    def callSystemCommand(self, name):
        if "off" in name.lower():
            if self.safetyCheck("run '" + name + "'"):
                return

        cmd = urllib.parse.quote(name)
        self.sendPostRequest("system/commands/custom/" + cmd, '')

    # only used internally (passed to caller as a pointer)
    def setPower(self, name):
        if "off" in name.lower():
            if self.safetyCheck(name):
                return

        cmd = "turnPSUOff"
        if "on" in name.lower():
            cmd = "turnPSUOn"

        return self.sendPostRequest("plugin/psucontrol", '{ "command":"' + cmd + '" }')

    # should automatically turn on printer, regardless of method
    def turnOn(self):
        if self.method == "psucontrol":
            self.setPower("on")
        elif self.method == "system":
            cmds = self.getSystemCommands()
            for cmd in cmds:
                if "on" in cmd:
                    self.callSystemCommand(cmd)
                    break

    # should automatically turn off printer, regardless of method
    def turnOff(self):
        if self.method == "psucontrol":
            self.setPower("off")
        elif self.method == "system":
            cmds = self.getSystemCommands()
            for cmd in cmds:
                if "off" in cmd:
                    self.callSystemCommand(cmd)
                    break

    ######################
    # Status Information #
    ######################

    # only used internally
    def getTemperatureIsSafe(self, limit = 50.0):
        r = self.sendGetRequest("printer")
        try:
            rd = json.loads(r)

            if "temperature" in rd:
                if ("tool0" in rd["temperature"]) and ("actual" in rd["temperature"]["tool0"]):
                    if rd["temperature"]["tool0"]["actual"] > limit:
                        return False

                if ("tool1" in rd["temperature"]) and ("actual" in rd["temperature"]["tool1"]):
                    if rd["temperature"]["tool1"]["actual"] > limit:
                        return False
        except json.JSONDecodeError:
            pass
        return True

    # human readable temperatures
    def getTemperatureString(self):
        r = self.sendGetRequest("printer")
        s = ""
        try:
            rd = json.loads(r)
        except json.JSONDecodeError:
            return s

        if ("state" in rd) and ("text" in rd["state"]):
            s += rd["state"]["text"]
            if "temperature" in rd:
                s += " - "

        if "temperature" in rd:
            if ("bed" in rd["temperature"]) and ("actual" in rd["temperature"]["bed"]):
                s += "B"
                s += "%.1f" % rd["temperature"]["bed"]["actual"]
                if "target" in rd["temperature"]["bed"]:
                    s += "/"
                    s += "%.1f" % rd["temperature"]["bed"]["target"]
                s += " "

            if ("tool0" in rd["temperature"]) and ("actual" in rd["temperature"]["tool0"]):
                s += "T"
                s += "%.1f" % rd["temperature"]["tool0"]["actual"]
                if "target" in rd["temperature"]["tool0"]:
                    s += "/"
                    s += "%.1f" % rd["temperature"]["tool0"]["target"]
                s += " "

            if ("tool1" in rd["temperature"]) and ("actual" in rd["temperature"]["tool1"]):
                s += "T"
                s += "%.1f" % rd["temperature"]["tool1"]["actual"]
                if "target" in rd["temperature"]["tool1"]:
                    s += "/"
                    s += "%.1f" % rd["temperature"]["tool1"]["target"]
                s += " "
        return s.strip()

    # only used internally
    def getState(self):
        r = self.sendGetRequest("job")
        try:
            rd = json.loads(r)
            if "state" in rd:
                return rd["state"]
        except json.JSONDecodeError:
            pass
        return "Unknown"

    # only used internally
    def getProgress(self):
        r = self.sendGetRequest("job")
        try:
            rd = json.loads(r)
            if "progress" in rd:
                return rd["progress"]
        except json.JSONDecodeError:
            pass
        return "Unknown"

    # human readable name (fall back to hostname)
    def getName(self):
        r = self.sendGetRequest("printerprofiles")
        try:
            rd = json.loads(r)
            if "profiles" in rd:
                p = next(iter(rd["profiles"]))
                if "name" in rd["profiles"][p]:
                    return rd["profiles"][p]["name"]
        except json.JSONDecodeError:
            pass
        return self.host

    # human readable progress
    def getProgressString(self):
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

    def callHoming(self, axes = "xyz"):
        if self.stateSafetyCheck("home it"):
            return

        axes_string = ''
        for i in range(0, len(axes)):
            axes_string += '"' + str(axes[i]) + '"'
            if i < (len(axes) - 1):
                axes_string += ', '

        self.sendPostRequest("printer/printhead", '{ "command": "home", "axes": [' + axes_string + '] }')

    def callMove(self, axis, dist, speed, relative = True):
        if self.stateSafetyCheck("move it"):
            return

        absolute = ''
        if relative == False:
            absolute = ', "absolute": true'

        self.sendPostRequest("printer/printhead", '{ "command": "jog", "' + str(axis) + '": ' + str(dist) + ', "speed": ' + str(speed) + absolute + ' }')

    def callPauseResume(self):
        if self.stateSafetyCheck("pause/resume"):
            return
        self.sendPostRequest("job", '{ "command": "pause", "action": "toggle" }')

    def callJobCancel(self):
        if self.stateSafetyCheck("cancel"):
            return
        self.sendPostRequest("job", '{ "command": "cancel" }')

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
        r = self.sendGetRequest("files?recursive=true")
        files = []
        try:
            rd = json.loads(r)
            if "files" in rd:
                t = [f for f in rd["files"] if "date" in f]
                fs = sorted(t, key=operator.itemgetter("date"), reverse=True)
                for f in fs[:count]:
                    files.append((f["name"], f["origin"] + "/" + f["path"]))
        except json.JSONDecodeError:
            pass
        return files

    def printFile(self, path):
        self.sendPostRequest("files/" + path, '{ "command": "select", "print": true }')

    ###############
    # Temperature #
    ###############

    # only used internally
    def setTemperature(self, what, temp):
        if temp == None:
            temp = 0

        path = "printer/bed"
        s = "{\"command\": \"target\", \"target\": " + str(temp) + "}"

        if "tool" in what:
            path = "printer/tool"
            s = "{\"command\": \"target\", \"targets\": {\"" + str(what) + "\": " + str(temp) + "}}"

        self.sendPostRequest(path, s)

    def printerHeatTool(self, temp):
        self.setTemperature("tool0", temp)

    def printerHeatBed(self, temp):
        self.setTemperature("bed", temp)

    def printerCooldown(self):
        if self.stateSafetyCheck("cool it down"):
            return

        self.setTemperature("tool0", 0)
        self.setTemperature("bed", 0)

    ##########
    # Webcam #
    ##########

    def getWebcamURL(self):
        return "http://" + self.host + ":8080/?action=snapshot"
