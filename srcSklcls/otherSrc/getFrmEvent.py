#! /usr/bin/env python
#coding=utf-8
import time
import re
import os
import sys
import math
import cPickle

class Event:
    def __init__(self, eventId):
        self.eventId = eventId
    
    def updateEvent(self, nodeHash, edgeHash):
        self.nodeHash = nodeHash
        self.edgeHash = edgeHash

############################
## load seg pair
def loadsegPair(filepath):
    inFile = file(filepath,"r")
    segmentHash = cPickle.load(inFile)
    segPairHash = cPickle.load(inFile)
    inFile.close()
    return segmentHash, segPairHash

############################
## load wikiGram
def loadWiki(filepath):
    global wikiProbHash
    inFile = file(filepath,"r")
    while True:
        lineStr = inFile.readline()
        lineStr = re.sub(r'\n', ' ', lineStr)
        lineStr = lineStr.strip()
        if len(lineStr) <= 0:
            break
        prob = float(lineStr[0:lineStr.find(" ")])
        gram = lineStr[lineStr.find(" ")+1:len(lineStr)]
#        print gram + "\t" + str(prob)
        wikiProbHash[gram] = prob
    inFile.close()
    print "### " + str(time.asctime()) + " " + str(len(wikiProbHash)) + " wiki grams' prob are loaded from " + inFile.name

############################
## keep top K (value) items in hash
def getTopItems(sampleHash, K):
    sortedList = sorted(sampleHash.items(), key = lambda a:a[1], reverse = True)
    sampleHash.clear()
    sortedList = sortedList[0:K]
    for key in sortedList:
        sampleHash[key[0]] = key[1]
    return sampleHash

############################
## cluster Event Segment
def clusterEventSegment(dataFilePath, kNeib, taoRatio):
    fileList = os.listdir(dataFilePath)
    for item in sorted(fileList):
        if item.find("relSkl_2013") != 0:
            continue
        tStr = item[-2:]
        if tStr != Day:
            continue
        print "Time window: " + tStr
        segPairFilePath = dataFilePath + "segPairFile" + tStr
        [segmentHash, segPairHash] = loadsegPair(segPairFilePath)

        print "### " + str(time.asctime()) + " " + str(len(segmentHash)) + " event segments in " + segPairFilePath  + " are loaded. With segment pairs Num: " + str(len(segPairHash))

        # get segments' k nearest neighbor
        kNNHash = {}
        for pair in segPairHash:
            sim = segPairHash[pair]
            segArr = pair.split("|")
            segId1 = int(segArr[0])
            segId2 = int(segArr[1])
            nodeSimHash = {}
            if segId1 in kNNHash:
                nodeSimHash = kNNHash[segId1]
            nodeSimHash[segId2] = sim
            if len(nodeSimHash) > kNeib:
                nodeSimHash = getTopItems(nodeSimHash, kNeib)
            kNNHash[segId1] = nodeSimHash

            nodeSimHash2 = {}
            if segId2 in kNNHash:
                nodeSimHash2 = kNNHash[segId2]
            nodeSimHash2[segId1] = sim
            if len(nodeSimHash2) > kNeib:
                nodeSimHash2 = getTopItems(nodeSimHash2, kNeib)
            kNNHash[segId2] = nodeSimHash2
        print "### " + str(time.asctime()) + " " + str(len(kNNHash)) + " event segments' " + str(kNeib) + " neighbors are got."

        # cluster similar segments into events
        eventHash = {}
        eventIdx = 0
        nodeInEventHash = {}
        for segId1 in kNNHash:
            nodeSimHash = kNNHash[segId1]
 #           print "#############################segId1: " + str(segId1)
 #           print nodeSimHash
            for segId2 in nodeSimHash:
                if segId2 in nodeInEventHash:
                    # s2 existed in one cluster, no clustering again
                    continue
 #               print "*************segId2: " + str(segId2)
 #               print kNNHash[segId2]
                #[GUA] should also make sure segId2 in kNNHash[segId1]
                if segId1 in kNNHash[segId2]:
                    # s1 s2 in same cluster


                    #[GUA] edgeHash mapping: segId + | + segId -> simScore
                    #[GUA] nodeHash mapping: segId -> edgeNum
                    #[GUA] nodeInEventHash mapping: segId -> eventId
                    eventId = eventIdx
                    nodeHash = {}
                    edgeHash = {}
                    event = None
                    if segId1 in nodeInEventHash:
                        eventId = nodeInEventHash[segId1]
                        event = eventHash[eventId]
                        nodeHash = event.nodeHash
                        edgeHash = event.edgeHash
                        nodeHash[segId1] += 1
                    else:
                        eventIdx += 1
                        nodeInEventHash[segId1] = eventId
                        event = Event(eventId)
                        nodeHash[segId1] = 1
                    nodeHash[segId2] = 1
                    if segId1 < segId2:
                        edge = str(segId1) + "|" + str(segId2)
                    else:
                        edge = str(segId2) + "|" + str(segId1)
                    edgeHash[edge] = segPairHash[edge]
                    event.updateEvent(nodeHash, edgeHash)
                    eventHash[eventId] = event
                    nodeInEventHash[segId2] = eventId
            # seg1's k nearest neighbors have been clustered into other events Or
            # seg1's k nearest neighbors all have long distance from seg1
            if segId1 in nodeInEventHash:
                continue
            eventId = eventIdx
            eventIdx += 1
            nodeHash = {}
            edgeHash = {}
            event = Event(eventId)
            nodeHash[segId1] = 1
            event.updateEvent(nodeHash, edgeHash)
            eventHash[eventId] = event
            nodeInEventHash[segId1] = eventId
        print "### " + str(time.asctime()) + " " + str(len(eventHash)) + " events are got with nodes " + str(len(nodeInEventHash))
        reverseSegHash = dict([(segmentHash[seg], seg) for seg in segmentHash.keys()])

        #'''
        # filtering
        segmentNewWorthHash = {}
        mu_max = 0.0
        mu_eventHash = {}
        for eventId in sorted(eventHash.keys()):
            event = eventHash[eventId]
            nodeList = event.nodeHash.keys()
            edgeHash = event.edgeHash
            segNum = len(nodeList)
            mu_sum = 0.0
            sim_sum = 0.0
            contentArr = [reverseSegHash[id] for id in nodeList]
            currNewWorthHash = {}
            for segment in contentArr:
                mu_s = segNewWorth(segment)
                segmentNewWorthHash[segment] = mu_s
                currNewWorthHash[segment] = mu_s
                mu_sum += mu_s

            for edge in edgeHash:
                sim_sum += edgeHash[edge]
            mu_avg = mu_sum/segNum
            sim_avg = sim_sum/segNum
            mu_e = mu_avg * sim_avg
            if mu_e > 0:
                mu_eventHash[eventId] = mu_e
                if False:
                #if True: # print temporal result mu(e) > 0
                    print "### event " + str(eventId) + " node|edge: " + str(segNum) + "|" + str(len(edgeHash)) + " mu_e: " + str(mu_e) + " mu_avg: " + str(mu_avg) + " sim_avg: " + str(sim_avg)
                    print sorted(currNewWorthHash.items(), key = lambda a:a[1], reverse = True)
            if mu_e > mu_max:
                mu_max = mu_e
        print "### Aft filtering 0 mu_e " + str(len(mu_eventHash)) + " events are kept. mu_max: " + str(mu_max)
        validEventHash = {}
        for eventId in mu_eventHash:
            mu_e = mu_eventHash[eventId]
            if mu_max * mu_e == 0:
                continue
            #validEventHash[eventId] = mu_max/mu_e
            if mu_max/mu_e < taoRatio:
                validEventHash[eventId] = mu_max/mu_e
        filteredEventHash = dict([(eId, eventHash[eId]) for eId in validEventHash])
        #'''
        
        eventFile = file(dataFilePath + "EventFile" + tStr + "_k" + str(kNeib) + "t" + str(taoRatio), "w")
        '''
        # output events
        eventFile = file(dataFilePath + "EventFile" + tStr + "_k" + str(kNeib) + "t" + str(taoRatio), "w")
        for eventID in eventHash:
            nodeHash = eventHash[eventID].nodeHash
            if len(nodeHash) < 2:
                continue
            edgeHash = eventHash[eventID].edgeHash
            segList = [reverseSegHash[id] for id in nodeHash.keys()]
            #print "*******Event " + str(eventID) + " node " + str(len(nodeHash)) + " edge " + str(len(edgeHash))
            #print " ".join(segList)
            eventFile.write("*******Event " + str(eventID) + " node " + str(len(nodeHash)) + " edge " + str(len(edgeHash)) + "\n")
            eventFile.write(" ".join(segList) + "\n")
            #print "\n"
            eventFile.write("\n")
        '''

        #'''
        sortedEventlist = sorted(validEventHash.items(), key = lambda a:a[1])
        eventNum = 0
        nodeLenHash = {}
        eventNumHash = {}
        for eventItem in sortedEventlist:
            eventNum += 1
            eventId = eventItem[0]
            event = filteredEventHash[eventId]
            edgeHash = event.edgeHash
            nodeHash = event.nodeHash
            nodeList = event.nodeHash.keys()
            nodeNewWorthHash = dict([(segId, segmentNewWorthHash[reverseSegHash[segId]]) for segId in nodeList])
            rankedNodeList_byNewWorth = sorted(nodeNewWorthHash.items(), key = lambda a:a[1], reverse = True)
            rankedNodeList = sorted(nodeHash.items(), key = lambda a:a[1], reverse = True)
            newNodeList = [key[0] for key in rankedNodeList]
            segList = [reverseSegHash[id] for id in newNodeList]
            segList_byNewWorth = [reverseSegHash[key[0]] for key in rankedNodeList_byNewWorth]
            nodes = len(nodeList)
            if nodes in nodeLenHash:
                nodeLenHash[nodes] += 1
            else:
                nodeLenHash[nodes] = 1
            if False:
            #if True:
                print "#################### event " + str(eventId) + " ratio: " + str(eventItem[1]),
                print " " + str(len(nodeList)) + " nodes and " + str(len(edgeHash)) + " edges."
                print rankedNodeList
                print "|".join(segList)
                print segList_byNewWorth
                print str(edgeHash)
            eventFile.write("****************************************\n###Event " + str(eventNum) + " ratio: " + str(eventItem[1]))
            eventFile.write( " " + str(len(nodeList)) + " nodes and " + str(len(edgeHash)) + " edges.\n")
            eventFile.write(str(rankedNodeList) + "\n")
            eventFile.write("||".join(segList) + "\n")
            eventFile.write("||".join(segList_byNewWorth) + "\n")
            eventFile.write(str(edgeHash) + "\n")
            ratioInt = int(eventItem[1])
            if ratioInt > 10:
                continue
            if ratioInt in eventNumHash:
                eventNumHash[ratioInt] += 1
            else:
                eventNumHash[ratioInt] = 1

        print "*************** " + str(len(filteredEventHash)) + " events, taoRatio " + str(taoRatio) + ", k " + str(kNeib)
        print "Event num < ratio: ",
        for ratioInt in sorted(eventNumHash.keys()):
            if ratioInt-1 in eventNumHash:
                eventNumHash[ratioInt] += eventNumHash[ratioInt-1]
        print sorted(eventNumHash.items(), key = lambda a:a[0])
        print "Event contained nodes num distribution: ",
        print sorted(nodeLenHash.items(), key = lambda a:a[1], reverse = True)
        #'''
        print "### " + str(time.asctime()) + " k = " + str(kNeib) + ". Events detected are stored into " + eventFile.name
        eventFile.close()

############################
## newsWorthiness
def segNewWorth(segment):
    wordArr = segment.split("_")
    wordNum = len(wordArr)
    if wordNum == 1:
        if segment in wikiProbHash:
            return math.exp(wikiProbHash[segment])
        else:
            return 0.0
    maxProb = 0.0

    for i in range(0, wordNum):
        for j in range(i+1, wordNum+1):
            subArr = wordArr[i:j]
            prob = 0.0
            subS = " ".join(subArr)
            if subS in wikiProbHash:
                prob = math.exp(wikiProbHash[subS]) - 1.0
            if prob > maxProb:
                maxProb = prob
#    if maxProb > 0:
#        print "Newsworthiness of " + segment + " : " + str(maxProb)
    return maxProb

############################
## main Function
print "###program starts at " + str(time.asctime())
if len(sys.argv) == 2:
    Day = sys.argv[1]
    print "##processing Day: "+ Day
else:
    print "Usage getEvent.py day"
    sys.exit()
wikiProbHash = {}
#dataFilePath = r"../parsedTweet/"
dataFilePath = r"../relnew/"

toolDirPath = r"../Tools/"
wikiPath = toolDirPath + "anchorProbFile_all"
kNeib = 5
taoRatio = 2
loadWiki(wikiPath)
clusterEventSegment(dataFilePath, kNeib, taoRatio)

# for choosing suitable parameters
#for kNeib in range(4,7):
#    clusterEventSegment(dataFilePath, kNeib, taoRatio)
#for taoRatio in range(3,6):
#    clusterEventSegment(dataFilePath, kNeib, taoRatio)

print "###program ends at " + str(time.asctime())
