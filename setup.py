from setuptools import setup

APP = ['macstress.py']
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'CFBundleName': 'MacStress',
        'CFBundleDisplayName': 'MacStress',
        'CFBundleIdentifier': 'com.macstress.app',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '12.0',
        'NSAppleEventsUsageDescription': 'MacStress needs administrator access to read power consumption data.',
    },
    'packages': ['objc', 'AppKit', 'Foundation', 'WebKit'],
    'includes': ['objc', 'AppKit', 'Foundation', 'WebKit',
                 'AppKit._AppKit', 'Foundation._Foundation', 'WebKit._WebKit'],
    'frameworks': [],
}

setup(
    app=APP,
    name='MacStress',
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
