# qppo2_viz.py

# create graphs for qppo2

import datetime
import numpy as np
import pandas as pd
import pickle
import matplotlib.pyplot as plt

######################### load data from pickle #########################
# set path to folder
date = datetime.date.isoformat(datetime.date.today())
path = 'results/' + date + '/data.pkl'

# load in pickle
with open(path, 'rb') as handle:
	[sev12, sev3, rem, qppo2, sev_errors] = pickle.load(handle)

# print(sev3.head())

######################### Set up dataframes #########################

sev3['reportedDate'] = sev3['Reported Date']
cols = ['reportedDate', 'daysOpen']
sev3 = sev3.filter(cols)[sev3.weekly_or_RCA == False]

# set baseline
sev3['baseline'] = 21

# set vars to something easy
inc_time = sev3.reportedDate       #X
res_time = sev3.daysOpen           #Y

# dumb date down to just day of incident
sev3.reportedDate = sev3.reportedDate.apply(lambda x: x.date())

# take daily average
grouped = sev3.groupby('reportedDate')
grouped = grouped.mean()

# 7-day rolling avg
r = grouped.rolling(window=7).mean()

######################### plot of resolution time over time #########################

# set style
plt.style.use('bmh') 
# plt.style.use('fivethirtyeight')

# plot
plt.figure(1)

# plot raw data points
plt.plot(sev3.reportedDate, sev3.daysOpen, 'o', label='Incident Resolution Time')

# plot baseline
plt.plot(r.baseline, '-', label="Technical Specification Limit")

# plot rolling average
plt.plot(r.daysOpen, '-', color='#D55E00', label='7-Day Rolling Average')

# set x and y limits
jan1 = str(datetime.date.today().year) + '-01-01'
plt.xlim([jan1, date])
plt.ylim([0, 35])

# format stuff
plt.xlabel('Date Reported')
plt.ylabel('Time to Resolve Incident (days)')
plt.title('SEV3 Incident Resolution Over Time, 2017')
plt.legend(loc='best', fontsize='x-small')
plt.xticks(rotation=45)

# path to save figure
path = 'results/' + date

# save figure
plt.savefig(path + '/QPPO2.png', bbox_inches='tight', dpi=600)
# plt.show()







