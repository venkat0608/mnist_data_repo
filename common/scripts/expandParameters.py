
# Below script will expand the CSV of parameters.This provides simple expansion of the parameters. The format is how we define ranges. There could be only one range per record or we throw exception to the user. Each record with range should expand to multiple rows where all other values remain constant and the column with the range is changing its value per the step within the ranges. Also we add a trial number that is restarted from 1 for each input row.
# Symbol usgae is as follows: \t separate between fields , | separate between or values , comma is regular char e.g. : \t for field separation, A|B|C is three records with A , then B, then C and A,B, C is just a regular string. ":" for defining ranges
# for more details refer to JIRA: https://jira.operasolutions.com/jira/browse/VEKTORPLATFORM-12940
# If foldNum parameter is given , it will generate foldNum replicas for each output record, adding a new foldID column with number between 0 to foldNum for each replica. Refer to JIRA: https://jira.operasolutions.com/jira/browse/VEKTORPLATFORM-14537

from decimal import *

def init():
    symbolDict = {}
    # 2 symbols decided to used for micro format
    symbolDict["pipe"] = "|";   
    symbolDict["colon"] = ":";
    return  symbolDict

def generateData( input, output, args, lookup ):
    foldNum = checkFoldNumIsNumeric(args)
    for rec in input:
        rec = rec.toDict()
        out = {}
        outputPushed = False
        #Check if multiple range exist in a row
        validateRec(rec,lookup)
        recCopy = rec
        for k,v in rec.iteritems():
            newSplitValues = []
            trialNumCounter = 1
            if lookup["colon"] in str(v):
                #This means it is a range 
                newSplitValues = getValuesFromRange(v,lookup["colon"], rec)

            #This means group of values, just need to split it
            elif lookup["pipe"] in str(v):
                newSplitValues = splitValues(v,lookup["pipe"])
            if len(newSplitValues) > 0:
                for val in newSplitValues:
                    out = {}
                    for k2,v2 in recCopy.iteritems():
                        if k2 == k:
                            out[k2] = val
                        else:
                            out[k2] = v2
                    out["trialNum"] = trialNumCounter
                    trialNumCounter = trialNumCounter + 1
                    if("foldNum" in args.keys()):
                        generateFoldNumReplicas(foldNum,out,output)
                    else:
                        output.push(out)
                    outputPushed = True    
            else:    
                out[k] = v
        if not outputPushed:
            out["trialNum"] = trialNumCounter
            if("foldNum" in args.keys()):
                generateFoldNumReplicas(foldNum,out,output)
            else:     
                output.push(out)
                

def checkFoldNumIsNumeric(args):
    try:
        if("foldNum" in args.keys()):
            return int(args['foldNum']) 
    except:
        raise_error("foldNum parameter value can't be alphanumeric. It should be numeric only. Currently it is set to '%s'" %(args['foldNum']))
            
def generateFoldNumReplicas(foldNum,out,output):
    for i in range(foldNum):
        out["foldID"] = i
        output.push(out)
             
def validateRec(rec,symbolDict):
    count =0 
    for k1,v1 in rec.iteritems():
        if symbolDict["colon"] in str(v1) or symbolDict["pipe"] in str(v1):
            count = count +1
    if count > 1:
        raise_error("Only one range allowed per record. More than one range exist because of multiple or combined use of symbol '- or |' in '%s' " %(rec))          
                        
def splitValues(column,symbol):
    return column.split(symbol)
 
def getValuesFromRange(column,rangeSymbol,rec):
    splitterSymbol = ","
    newSplitValues = []
    if splitterSymbol in column:
        # Splitting based on splitter symbol to separate range and increment information

        rangeStr = column.split(splitterSymbol)[0].strip()
        incrementStr= column.split(splitterSymbol)[1].strip()
    
        
        try:   
            start = rangeStr.split(rangeSymbol,1)[0].strip()
            end = rangeStr.split(rangeSymbol,1)[1].strip()   
        except:
            raise_error("Range has not been specified correctly for column '%s'. Specify correct range using format 'start-end,increment++' or 'start-end,decrement--' " %(rec))

        if not str(incrementStr)[0] == "." and not str(incrementStr)[0].isdigit():
            raise_error("Range 'increment' part is not specified properly for record '%s'.Specify correct range using format 'start-end,increment++' or 'start-end,decrement--' " %(rec))    
        #Get the increment
        increment = getIncrementforLoop(incrementStr,rec).strip()

        isFloat = False
        if (increment.replace("-", "").isdigit() and start.replace("-", "").isdigit() and end.replace("-", "").isdigit() ):
            increment = int(increment)
            start = int(start)
            end = int(end)
        else:
            try:
                increment = float(increment)
                start = float(start)
                end = float(end)
                isFloat = True
            except:
                raise_error("Range is not defined properly for record '%s'. Specify correct range using format 'start-end,increment++' or 'start-end,decrement--'"%(rec))

        newSplitValues = frange(start, end, increment, isFloat, rec)
    else:
        raise_error("Missing symbol ',' which separates range from increment/decrement for rec value '%s'. Specify correct range using format 'start-end,increment++' or 'start-end,decrement--' " %(rec))    
    return newSplitValues

def frange(x, y, jump, isFloat, rec):
    newSplitValues = []
    # for positive range
    if jump > 0: 
        if x <= y : 
            while x <= y:
                newSplitValues.append(x)
                x = adjustJump(x, jump, isFloat )
        else:
            raise_error( "Incorrect value for 'start(%s)' greater than 'end(%s)' has been specified for 'positive increment(%s)' range in record '%s' Specify correct range using format 'start-end,increment++' or 'start-end,decrement--' " %(x,y,jump,rec))

    # for negative range
    else:
        if x >= y :
            while x >= y:
                newSplitValues.append(x)
                x = adjustJump(x, jump, isFloat )
        else:
            raise_error( "Incorrect value for 'start(%s)' lesser than 'end(%s)' has been specified for 'negative increment(%s)' range in record '%s' Specify correct range using format 'start-end,increment++' or 'start-end,decrement--' " %(x,y,jump,rec))               
    return newSplitValues

def adjustJump(x, jump, isFloat ):
    if(isFloat):
        # Because internally, computers use a format (binary floating-point) that cannot accurately represent a number like 0.1, 0.2 or 0.3 at all. Look at -> http://floating-point-gui.de/basic/. Solution is referred from : http://0.30000000000000004.com/
        x = float(Decimal(str(x)) + Decimal(str(jump)))
    else:
        x += jump
    return x

def raise_error(message):
    print "ERROR: "+ message
    raise Exception('Terminating program and raising an exception!') 

def getIncrementforLoop(incrementStr,rec):
    increment = ""    
    if "+" in incrementStr:
        increment = incrementStr[:-2]
    elif "-" in incrementStr:
        increment = "-" + incrementStr[:-2]
    else:
        raise_error("operand (+,-) is missing for range in record '%s'.Specify correct range using format 'start-end,increment++' or 'start-end,decrement--'. "%(rec))
    return increment    