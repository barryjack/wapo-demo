# get_data.py
# collect data from Remedy files
# Sort by Sev, return notable incidents for QPPO 1/2
# save in one .xls file

# import everything needed
import datetime
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import pickle
import os

######################### read in files from Remedy #########################
# get filenames
root = tk.Tk()
root.withdraw()
filepaths = filedialog.askopenfilename(multiple=True, message='Select New Remedy Extracts')

# create remedy dataframe
rem = pd.DataFrame()

# import files into pandas, put in one dataframe
# add filename to each element, so we can trace errors back
for filepath in filepaths:
	df = pd.read_csv(filepath, encoding="ISO-8859-1")
	df['filename'] = filepath
	rem = pd.concat([rem, df])

######################### get impact/urgency, sort out broken things #########################

# function to get impact/sort out misformatted data
def get_impact(incident):
	try:
		# assume it works, return just the numerical value of the impact/urgency
		return int(incident.Impact[0])
	except:
		# if it didn't work, make value nan
		# we will remove it from rem after
		return np.nan

# function to get urgency/sort out misformatted data
def get_urgency(incident):
	try:
		# assume it works, return just the numerical value of the urgency/urgency
		return int(incident.Urgency[0])
	except:
		# if it didn't work, make value nan
		# we will remove it from rem after
		return np.nan


# apply functions
rem['Impact'] = rem.apply(get_impact, axis=1)
rem['Urgency'] = rem.apply(get_urgency, axis=1)

# remove broken rows (indicated by null value in impact/urgency)
errors = rem[pd.isnull(rem.Impact)]
rem = rem[~pd.isnull(rem.Impact)]

# remove empty/unnamed columns
rem = rem[rem.columns[~rem.columns.str.contains('Unnamed:')]]
cols = ['Incident ID', 'Status', 'Priority', 'Notes', 'Reported Date', 'Assigned Group', 'Assignee', 'Resolution', 'Last Resolved Date', 'Responded Date', 'Last Modified Date', 'Impact', 'Urgency', 'Incident Type','filename', 'Summary']
rem = rem.filter(cols)

######################### sort by date, filter out broken things #########################

# attempt to convert strings of dates to datetime objects. coerce errors into NaT
rem['Last Resolved Date'] = pd.to_datetime(rem['Last Resolved Date'], errors='coerce')
rem['Last Modified Date'] = pd.to_datetime(rem['Last Modified Date'], errors='coerce')
rem['Reported Date'] = pd.to_datetime(rem['Reported Date'], errors='coerce')

# check to see what errors have been coerced into NaT values
# we don't check Last Resolved Date because that is allowed to be NaT
def date_errors(incident):
	return pd.isnull(incident['Last Modified Date']) or pd.isnull(incident['Reported Date'])

# apply function
rem['date_errors'] = rem.apply(date_errors, axis=1)

# add new errors to other dataframe, remove them from rem
errors = pd.concat([errors, rem[rem.date_errors == True]])
rem = rem[rem.date_errors == False]

# sort by date (most recent at top)
rem = rem.sort_values(by = 'Reported Date', ascending = False)


######################## separate incidents by severity #########################
# Columns we need to keep
cols = ['Incident ID','Reported Date','Last Modified Date','Last Resolved Date','Impact','Urgency','Resolution', 'date_errors', 'Assigned Group','Summary']

# break up incidents into different dataframes
# SEV1/2
sev12 = rem.filter(cols)[rem.Impact < 3]

# SEV3
sev3 = rem.filter(cols)[rem.Impact >= 3]

# # mismatched impact/urgency numbers
err_cols = ['Incident ID', 'Reported Date', 'Impact', 'Urgency', 'filename']
sev_errors = rem.filter(err_cols)[rem.Impact != rem.Urgency]

######################## Find total Days Open (QPPO2 analysis) #########################
# QPPO2: Close 100% of SEV3 incidents within 3 weeks of Reported data
# Want to separate out open non-RCA or weekly maintenance tickets

# find all incident tickets that are still open
sev3['stillOpen'] = pd.isnull(sev3['Last Resolved Date'])

# today's date
today = pd.to_datetime(datetime.date.today())

# function to figure out how many days an incident has been/was open:
def daysOpen(inc):
	try:
		# attempt to figure out how many days incident has been open
		if inc.stillOpen:
			# incident is still open -> subtract report date from today
			return today - inc['Reported Date']
		else:
			# incident closed -> subtract report date from resolved date
			return inc['Last Resolved Date'] - inc['Reported Date']
	except:
		# if fails, set daysOpen to be null (will be filtered out)
		return pd.NaT

# apply daysOpen function
sev3['daysOpen'] = sev3.apply(daysOpen, axis=1)

# add new errors to other dataframe, remove them from rem
errors = pd.concat([errors, sev3[pd.isnull(sev3.daysOpen)]])
sev3 = sev3[~pd.isnull(sev3.daysOpen)]


######################## sort out writereekly/RCA tickets #########################

# function to find tickets for weekly maintenance and RCA
def weekly_or_RCA(inc):
	if 'Weekly' in inc.Summary: return True
	elif 'RCA' in inc.Summary: return True
	else: return False

# function to return if an incident is a qppo2 concern
# this is defined as any sev3 incident that is still open and not a weekly
# maintenance or RCA ticket
def qppo2_concern(inc):
	w = inc['weekly_or_RCA']
	s = inc['stillOpen']
	return w == False and s == True

# apply 2 functions to check for weekly tickets & sort out qppo2 concerns
sev3['weekly_or_RCA'] = sev3.apply(weekly_or_RCA, axis=1)
sev3['qppo2_concern'] = sev3.apply(qppo2_concern, axis=1)

# columns we need to keep
cols = ['Incident ID','Reported Date','Last Modified Date','Last Resolved Date','daysOpen', 'Impact','Urgency','Resolution','Assigned Group','Summary']

# create separate df for qppo2
qppo2 = sev3.filter(cols)[sev3.qppo2_concern == True]
qppo2 = qppo2.sort_values(by = 'daysOpen', ascending = False)

# function to convert timedelta into a float for a number of days
def totalDays(inc):
	if pd.isnull(inc): return 0
	# convert timedelta to total number of hours
	else:
		total = (inc.days*24 + inc.seconds/3600)/24
		return total

# convert timedeltas to floats (so they can be graphed)
qppo2.daysOpen = qppo2.daysOpen.apply(totalDays)
sev3.daysOpen = sev3.daysOpen.apply(totalDays)

######################### create excel workbook tabs for data drill #########################

inc_mgmt_cols = ['Incident ID', 'Reported Date', 'Last Resolved Date']
data_qual_cols = ['Incident ID', 'Impact', 'Reported Date', 'Last Resolved Date']

inc_mgmt = sev3.filter(inc_mgmt_cols)[sev3.weekly_or_RCA == False]
inc_mgmt = inc_mgmt.sort_values(by = 'Reported Date', ascending = True)

data_qual = sev12.filter(data_qual_cols)
data_qual = data_qual.sort_values(by = 'Reported Date', ascending = True)

######################### write new .xls file #########################
date = datetime.date.isoformat(datetime.date.today())
# create new folder for results
# find filepath

# create new sub-folder
path = 'results/' + date
os.makedirs(path, exist_ok=True)

# new writer object
writer = pd.ExcelWriter(path + '/remedy_data.xls')

# add all sheets to excel document
sev12.to_excel(writer, 'SEV1, SEV2 Incidents')
sev3.to_excel(writer, 'SEV3 Incidents')
qppo2.to_excel(writer, 'Current QPPO2 Concerns')
sev_errors.to_excel(writer, 'SEV# mismatches')
rem.to_excel(writer, 'Remedy Output')
errors.to_excel(writer, 'Misformatted Data')
inc_mgmt.to_excel(writer, 'DD Incident Management')
data_qual.to_excel(writer, 'DD Data Quality')

# save xls
writer.save()


###################### Pickle errythang (for use by viz scripts) ######################

# dataframes we need to keep
data = [sev12, sev3, rem, qppo2, sev_errors]

# create pickle object
with open(path + '/data' + '.pkl', 'wb') as handle:
	pickle.dump(data, handle)





