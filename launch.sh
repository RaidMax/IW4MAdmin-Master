#!/bin/bash

pyver="$(python3 -V 2>&1 | grep -Po '(?<=Python )(.+)')"
requiredver="3.4"

if [[ -z "$pyver" ]]
then
	echo "Python 3 does not appear to be installed."
else
	if [[ $pyver =~ $requiredver ]]
	then
		echo "Python Version is $pyver"
		echo "Installing Requirements..."
		pip install -r requirements.txt
		python3 runserver.py
	else
		echo "Minimum Python version required is $requiredver"
	fi
fi
