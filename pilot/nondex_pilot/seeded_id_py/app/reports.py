import os


def first_report(directory):
    return os.listdir(directory)[0]               # ID: os.listdir returns entries in arbitrary order
