@echo off
cls
:my_loop
IF %1=="" GOTO completed
  python C:\addic7ed.py %1
  SHIFT
  GOTO my_loop
:completed