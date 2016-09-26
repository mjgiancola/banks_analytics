#!/usr/bin/python

################################### PREAMBLE ###################################

import csv
import sys
import argparse
import subprocess
import numpy as np
from sklearn import linear_model
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.cross_validation import train_test_split

from ModelResults import ModelResults	# Class I made for storing details (used for exporting to txt file, for creating graphs etc.)
					# It handles rounding/casting; just pass variables used as is
from export_test import *		# A file I wrote to export results to a txt file

# WARNING: Normally, large numpy arrays are truncated (ie. [ 1, 2, ... , 9999, 10000 ] )
#          This option turns this feature off, so that the entire array can be printed
#          BE CAREFUL WHAT YOU PRINT
np.set_printoptions(threshold=np.inf)
np.set_printoptions(precision=3) # This one is a lot less scary, just sets number of printed digits

################################## MODEL CODE ##################################

print("WPI/Deloitte Regression Model for Predicting License Revocation of Russian Banks\n")

# Argument Parsing
parser = argparse.ArgumentParser()
c_par = parser.add_mutually_exclusive_group()
c_par.add_argument("-c", "--pass_c", help="Pass in value for C for model to use.")
seed_par = parser.add_mutually_exclusive_group()
seed_par.add_argument("-s", "--seed", help="Pass seed for train_test_split.")
desc = parser.add_mutually_exclusive_group()
desc.add_argument("-d", "--description", help="Give text to describe model run type. Will be stored in description.txt")
c_test = parser.add_mutually_exclusive_group()
c_test.add_argument("-ct", "--c_test", help="Used by c_test.py to output several runs to one file; give this option the path to the file where all results should be stored")
args = parser.parse_args()

if args.description != None:
	generate_path() # Generate folders for path if they don't exist

	descFile = path + "description.txt"
	with open(descFile, "w") as fp:
		fp.write(args.description)
		fp.close()

call_parse = ["../parser/parser.py", "-s"]
features = ["return_on_net_assets", "return_on_equity"] # NOTE: Change *this* array to add features to model
call_parse += features

# Run parser to generate custom model_data.csv file
print("Generating datafile...")
try:
    subprocess.call(call_parse, cwd="../parser") # cwd = Current Working Directory
except WindowsError:
    subprocess.call(call_parse, cwd="../parser",shell = True) # cwd = Current Working Directory

print("Importing data...")
with open('../csv/model_data.csv', 'rb') as csvfile:
	my_reader = csv.reader(csvfile)	
	firstRow = True		# So that loop skips over first row (which contains header info)
	i = 0			# Keep track of loop number

	for row in my_reader:	# Iterate over all rows in csv
		if firstRow == False:
			
			target = float(row[2])	# Get target value from file
			if target > 0:		# Ignore negative targets (ie. values from after revocation)
				
				# Generate array of new features
				new_feat = []
				for j in range(3, numFeatures+3):	# Iterate over features, add to array
					curr_feat = row[j]

					# No data provided for this feature
					if curr_feat == "":
						new_feat.append(float(0))	# Meaningless value
						new_feat.append(float(0))	# 0 = Value missing

					else:
						# Boolean values provided (for reporting in bounds / out of bounds)
						if curr_feat == "True":
							new_feat.append(float(1))	# 1 = In Bounds 

						elif curr_feat == "False":
							new_feat.append(float(0))	# 0 = Out of Bounds

						# Numeric value provided (normal -- value of feature)
						else:
							new_feat.append(float(curr_feat)) # Use value of feature

						new_feat.append(float(1)) # 1 = Value present

				X = np.concatenate(( X, np.array([new_feat]) )) # Add new feature set to array
				Y = np.append(Y, target)			# Add new target to array

		else:
			firstRow = False
			numFeatures = len(row)-3 # Everything past first three columns are features

			# Create array of feature labels
			feature_labels = []
			for j in range(3, numFeatures+3):
				feature_labels.append(row[j])		# Add feature name
				feature_labels.append("%s_M?" % row[j])	# For missing column

			# Create the feature and target datasets respectively
			X = np.empty((0,numFeatures*2), float) # np.empty creates an empty array with shape attributes (so it can be used in concatenate)
			Y = np.array([])

		# Print dots to indicate progress		
		if i % 350 == 0:
			sys.stdout.write('.')
			sys.stdout.flush()
		i += 1

feature_labels = np.array(feature_labels) # Convert feature_labels to a numpy ndarray

print("\nFitting model...")

# Split data into testing & training, with 66% training, 33% testing
# If seed passed, use it
if args.seed != None:
	X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.33, random_state=int(args.seed), stratify=Y)
else:
	X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.33, stratify=Y)

# Store results in ModelResults object
results = ModelResults(X_train, X_test, Y_train, Y_test, feature_labels)

# If passed, use passed in C value
if args.pass_c != None: c_val = float(args.pass_c)
else:		      	c_val = 0.01

# Create the model & fit to training data
model = linear_model.LogisticRegression(penalty='l1', C=c_val, multi_class='ovr').fit(X_train, Y_train)

print("Generating predictions...")
predict_arr = model.predict(X_test)	  # Run a prediction for test dataset (ie. compare this array to Y_test)
prob_arr    = model.predict_proba(X_test) # Runs prediction, outputs probability vectors

print("Evaluating performance...")
precision = precision_score(Y_test, predict_arr, average=None)	# Calculate the precision
recall    = recall_score(Y_test, predict_arr, average=None)	# Calculate the recall
f1        = f1_score(Y_test, predict_arr, average=None)		# Calculate f1

results.addResults(c_val, model.coef_, predict_arr, prob_arr, precision, recall, f1) # Add results to "results" object

# If C value passed in, add results to file (used in script for testing several values of C)
if args.c_test != None:
	export_c_test(results, args.c_test)
	exit() # Quit early so full results aren't exported

print("\nC: %s\n" % c_val)
print("Precision: %s\n" % precision)
print("Recall: %s\n" % recall)
print("f1: %s\n" % f1)

print("Exporting results...")
export_test(results)
print("Data sets and results exported to %s" % path)

################################################################################
