@REM D:\CV\MYTOOL\MANAGER_TOOL\toolExt\adb.exe shell dumpsys window | findstr mCurrentFocus

.\toolExt\adb.exe shell am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.google.android.gm