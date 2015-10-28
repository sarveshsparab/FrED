#! /usr/bin/env python
#coding=utf-8
# function: for calculating similarity between two segments/skeletons when clustering them
import time
import re
import os
import cPickle
import sys


############################
## main Function
if __name__ == "__main__":

    if len(sys.argv) == 2:
        inputDir = sys.argv[1]
        outputDir = inputDir
    elif len(sys.argv) == 3:
        inputDir = sys.argv[1]
        outputDir = sys.argv[2]
    else:
        print "Usage: python statisticWordDf.py inputDir(eg. ~/corpus/data_twitter201301/201301_clean) [outputDir default:=inputDir]"
        sys.exit(0)

    wordDFFile = file(outputDir + r"/wordDF", "w")

    wordDFHash = {}
    wordAppHash = {}

    for tStr in xrange(1, 31):
        tStr = str(tStr).zfill(2)
        textFile = file(inputDir + r"/tweetCleanText"+tStr)
    #    textFile = file(inputDir + r"/text_2013-01-"+tStr)
        #textFile = file(inputDir + r"/relSkl_2013-01-"+tStr)
        print "Processing " + textFile.name
        idx = 0
        while True:
            lineStr = textFile.readline()
            lineStr = re.sub(r'\n', " ", lineStr)
            if len(lineStr) <= 0:
                print "## loading done. " + str(time.asctime()) + textFile.name
                break

            arr1 = lineStr.strip().split("\t")
            tid = arr1[0]
            text = re.sub(r"_", " ", arr1[1])
            arr = text.lower().split(" ")

            for w in arr:
                if w in wordAppHash:
                    wordAppHash[w].update(dict([(tid, 1)]))
                else:
                    wordAppHash[w] = dict([(tid, 1)])
                    wordDFHash[w] = 0
            idx += 1
            if idx % 100000 == 0:
                print "### " + str(time.asctime()) + " " + str(idx) + " tweets are processed!"

        textFile.close()

    for w in wordDFHash:
        wordDFHash[w] = len(wordAppHash.pop(w))

    cPickle.dump(wordDFHash, wordDFFile)
    wordDFFile.close()

    print "Program ends. " + str(time.asctime()) + " " + str(len(wordDFHash)) + " words are obtained! Writen into " + wordDFFile.name
