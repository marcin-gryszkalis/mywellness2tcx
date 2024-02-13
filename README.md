# Convert treadmill or indoor bike activity from MyWellness JSON format to TCX

`mywellness2tcx.py` script converts treadmill acivity data including HR and Elevation/Altitude in MyWellness JSON format to TCX suitable to import to Strava, Trainingpeaks, etc., and its sole reason for existing is because technogym is incapable of creating anything useful but hardware.

## Usage

1. Go to [https://www.mywellness.com/cloud/Training](https://www.mywellness.com/cloud/Training).
2. Open Developer Tools window in your browser, switch to Network tab, select XHR filter.
3. Click on a circle with number to expand activities for needed date, go to activity page.
4. Right click on last request in Developer Tools window (`GET https://services.mywellness.com/Training/CardioLog/…/Details?…`), choose Copy response.
5. Save copied data into file.
6. Run `mywellness2tcx.py JSON_FILE ACTIVITY_START_TIME`, where JSON_FILE is the path to the file you just saved and ACTIVITY_START_TIME is UTC start time for the activity in `%Y-%m-%dT%H:%M` format.
7. There schould `.tcx` file appear in the same folder as JSON_FILE. Upload it to whatever service you please.

## Download all activities

1. Go to [https://www.mywellness.com/cloud/Training](https://www.mywellness.com/cloud/Training).
2. Open Developer Tools window in your browser, switch to Application tab, select Cookies and copy value of `_mwappseu` cookie.
3. Run `perl get-all.pl 1 10 'xxxx'` where `1` and `10` specify range of activities to download and `xxxx` is value of cookie.
4. After download you can convert all activities with main script, note `19:00` in example below - they all will have the same start time
```
ls mywellness*json | perl -nle '$d = (s/.*(\d\d\d\d-\d\d-\d\d).*/$1T19:00/r); print `python mywellness2tcx.py "$_" "$d"`'
```
