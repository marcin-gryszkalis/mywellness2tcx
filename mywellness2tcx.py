#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import json
import sys
import math
import re
from xml.etree import ElementTree as et


TCD_NS = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
AX_NS = 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'



def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

# altitude simulation for simple indoor bicycle with manual setting of resistance, measured 1-20
# negative for level 5 and below, 0% for level 6, 10% for level 20 (max)
def level2grade(l):
    # return round(1.1330 ** l - 2, 2) -- exponential is too flat
    return math.tan(l/7.35 - 4.52) * 2 + 1.3

def mywellness2tcx(in_file, out_file, start_dt, initialAltitude):
    lastCadence = "0"
    lastRpm = "0"
    lastPower = "0"
    lastHr = "0"
    lastAltitude = str(initialAltitude)
    lastDistance = "0"
    inclinePercent = "0"
    inclineDegrees = "0"

    with open(in_file) as fp:
        data = json.load(fp)

    try:
        analitics = data['data']['analitics']
        fields = [
            descriptor['pr']['name']
            for descriptor in analitics['descriptor']
        ]
    except:
        print('No Data Points found. Please make sure you use the JSON from the dev tools instead of the download from mywellness.com')
        sys.exit(1)


    sport = 'Running'
    if re.search(r'(?i)bike', data['data']['equipmentType']):
        sport = 'Biking'

    samples = []
    for sample in analitics['samples']:
        dt = start_dt + timedelta(seconds=sample['t'])
        values = dict(zip(fields, sample['vs']))
        values['t'] =  sample['t']
        samples.append((dt, values))

    # Strip point at the end with no activity
    while samples:
        dt, sample = samples[-1]
        if sample['Speed'] != 0 or sample['Power'] != 0:
            break
        samples.pop()

    # Distances in HDistance are very inaccurate.  Loading them to Strava will
    # lead to calculated speed having interchanging 0 and 72 km/h values only
    # and sawtooth graph for it.

    # Calclulate distance from recorded speed data
    prev_dt, sample = samples[0]
    dist = sample['HDistance']
    for dt, sample in samples[1:]:
        dist += (dt - prev_dt).seconds * sample['Speed'] / 3.6
        prev_dt = dt

    # Correction factor to get the same total distance
    # TODO Do smoothing within moving window to get closer distances at eache
    # point, not just at the end.
    fact = sample['HDistance'] / dist
    # Something went wrong if it's not close to 1
    assert 0.95 < fact < 1.05

    # Recalculate distances once more, now with correction factor
    prev_dt, sample = samples[0]
    dist = sample['HDistance']
    sample['SmoothDistance'] = dist
    for dt, sample in samples[1:]:
        dist += (dt - prev_dt).seconds * sample['Speed'] / 3.6 * fact
        sample['SmoothDistance'] = dist
        prev_dt = dt

    # Dump the activity into XML
    tcd = et.Element('TrainingCenterDatabase', xmlns=TCD_NS)
    activities = et.SubElement(tcd, 'Activities')
    activity = et.SubElement(activities, 'Activity', Sport=sport)
    # Id field hase type xsd:dateTime!
    et.SubElement(activity, 'Id').text = iso(start_dt)
    lap = et.SubElement(activity, 'Lap', StartTime=iso(start_dt))
    track = et.SubElement(lap, 'Track')

    gradientSum = 0
    for dt, sample in samples:
        inclinePercent = 0
        inclineDegrees = 0
        point = et.SubElement(track, 'Trackpoint')
        et.SubElement(point, 'Time').text = iso(dt)
        et.SubElement(point, 'DistanceMeters').text = str(sample['SmoothDistance'])
        distanceDifference = (float(sample['SmoothDistance']) - float(lastDistance))
        lastDistance = sample['SmoothDistance']
        if ('Grade' in sample.keys()):
            inclinePercent = float(sample['Grade'])
            inclineDegrees = math.degrees(math.atan(inclinePercent/100))
            lastAltitude = str(float(lastAltitude) + ((distanceDifference * math.sin(math.radians(inclineDegrees))) / math.sin(math.radians(90))))
            #print(str(round(distanceDifference, 2)) + ' * sin(' + str(round(inclineDegrees, 2)) + ') / sin(90)) = ' + str(distanceDifference * math.sin(math.radians(inclineDegrees)) / math.sin(math.radians(90))))
        if ('Level' in sample.keys()):
            inclinePercent = level2grade(int(sample['Level']))
            inclineDegrees = math.degrees(math.atan(inclinePercent/100))
            lastAltitude = str(float(lastAltitude) + ((distanceDifference * math.sin(math.radians(inclineDegrees))) / math.sin(math.radians(90))))
        et.SubElement(point, 'AltitudeMeters').text = lastAltitude
        if ('RunningCadence' in sample.keys()):
            et.SubElement(point, 'Cadence').text = str(sample['RunningCadence'])
            lastCadence = str(sample['RunningCadence'])
        else:
            et.SubElement(point, 'Cadence').text = lastCadence
        if ('Rpm' in sample.keys()):
            et.SubElement(point, 'Cadence').text = str(sample['Rpm'])
            lastCadence = str(sample['Rpm'])
        else:
            et.SubElement(point, 'Cadence').text = lastCadence
        extensions = et.SubElement(point, 'Extensions')
        tpx = et.SubElement(extensions, 'TPX', xmlns=AX_NS)
        et.SubElement(tpx, 'Speed').text = str(sample['Speed'] / 3.6)
        if ('RunningPower' in sample.keys()):
            et.SubElement(tpx, 'Watts').text = str(sample['RunningPower'])
            lastPower = str(sample['RunningPower'])
        elif ('Power' in sample.keys()):
            et.SubElement(tpx, 'Watts').text = str(sample['Power'])
            lastPower = str(sample['Power'])
        else:
            et.SubElement(tpx, 'Watts').text = lastPower
        if ('hr' in analitics.keys()):
            for hr in analitics['hr']:
                if (int(sample['t']) <= int(hr['t'])):
                    lastHr = str(hr['hr'])
                    break
            hr = et.SubElement(point, 'HeartRateBpm')
            et.SubElement(hr, 'Value').text = lastHr
            print('New Waypoint: ➡️  ' + str(format('%05.2F' % round(float(distanceDifference),2))) + 'm \t ↗️  '+ str(format('%04.1F' % round(float(inclinePercent),2))) + '% (' + str(format('%04.1F' % round(float(inclineDegrees), 2))) + '°) \t ⬆️  ' + str(format('%04.1F' % round(float(lastAltitude), 2))) + 'm \t 🏎  ' + str(format('%04.1F' % round(sample['Speed'] / 3.6, 2))) + ' m/s \t 💪🏼  ' + str(format('%04.0F' % round(float(lastPower), 0))) + ' Watts \t ♥️  ' + str(lastHr) + 'bpm')
            gradientSum += round(float(distanceDifference),2) * round(float(inclinePercent),2)

    doc = et.ElementTree(tcd)
    print('Final Altitude was: ' + str(round(float(lastAltitude), 2)))
    print('Average gradient: ' + str(round(gradientSum / dist,2)) + "%")
    with open(out_file, 'wb') as out_fp:
        doc.write(out_fp, encoding='ascii', xml_declaration=True)
        print('Output file written.')


if __name__ == '__main__':
    in_file = sys.argv[1]
    base_name = (
        in_file[:-5] if in_file.lower().endswith('.json')
        else in_file
    )
    out_file = base_name + '.tcx'

    # There is no time in JSON and date is in localized format only
    start_dt = datetime.strptime(sys.argv[2], '%Y-%m-%dT%H:%M')

    # If provided, we'll pass on initial altitude (in meters) to the calculation.
    initialAltitude = 0.0
    try:
        if(sys.argv[3]):
            initialAltitude = float(sys.argv[3])
    except IndexError:
        print('No initial Altitude given, starting with 0')

    mywellness2tcx(in_file, out_file, start_dt, initialAltitude)
