#!/usr/bin/env python
# Copyright 2009 Yu-Jie Lin
# Copyright 2003 David McClosky
#
# This code is licensed under the GPLv3
#
# This Python code does not require any Python binding library, such as
# python-xlib or PyXSS. It directly accesses libXss via ctypes.
#
# It was written with intention of using PyXSS' IdleTracker but without PyXSS.
# You don't need to install PyXSS.
#
# Note:
# 1. The code isn't tested/finished completely, you might hit something if you
#    have two displays and/or your default screen isn't Screen 0.
# 2. For the information we do not need and their types are pointers, all are
#    set with c_void_p.
# 3. No error handling.
# 4. This is not a replacement of PyXSS.
#
# PyXSS' author is David McClosky and this script use a big chuck of code from
# it. You can download the PyXSS code at http://bebop.bigasterisk.com/python
#
# The rest of this script is written by Yu-Jie Lin ( http://livibetter.mp/ )


from ctypes import * 

libXss = None

for lib in ['libXss.so', 'libXss.so.1']:
    try:
        libXss = CDLL(lib)
    except OSError:
        pass

if libXss is None:
    raise OSError("Could not load libXss.so")

class Screen(Structure):
  _fields_ = [
      ('ext_data', c_void_p),         # XExtData *ext_data; /* hook for extension to hang data */
      ('display', c_void_p),          # struct _XDisplay *display;/* back pointer to display structure */
# X.h:101:typedef XID Window;
# X.h:71:typedef unsigned long XID;
      ('root', c_ulong),              # Window root;        /* Root window id. */
# We only need root, but we also need precise size of Screen to offset array index.
      ('width', c_int),               # int width, height;  /* width and height of screen */
      ('height', c_int),
      ('mwidth', c_int),              # int mwidth, mheight;    /* width and height of  in millimeters */
      ('mheight', c_int),
      ('ndepths', c_int),             # int ndepths;        /* number of depths possible */
      ('depths', c_void_p),           # Depth *depths;      /* list of allowable depths on the screen */
      ('root_depth', c_int),          # int root_depth;     /* bits per pixel */
      ('root_visual', c_void_p),      # Visual *root_visual;    /* root visual */
# GC is structure pointer
      ('default_gc', c_void_p),       # GC default_gc;      /* GC for the root root visual */
# X.h:109:typedef XID Colormap;
      ('cmap', c_ulong),              # Colormap cmap;      /* default color map */
      ('white_pixel', c_ulong),       # unsigned long white_pixel;
      ('black_pixel', c_ulong),       # unsigned long black_pixel;  /* White and Black pixel values */
      ('min_maps', c_int),            # int max_maps, min_maps; /* max and min color maps */
      ('backing_store', c_int),       # int backing_store;  /* Never, WhenMapped, Always */
      ('save_unders', c_bool),        # Bool save_unders;
      ('root_input_mask', c_long),    # long root_input_mask;   /* initial root input mask */
      ]


class Display(Structure):
  _fields_ = [
      ('ext_data', c_void_p),         # XExtData *ext_data; /* hook for extension to hang data */
      ('private1', c_void_p),         # struct _XPrivate *private1;
      ('fd', c_int),                  # int fd;         /* Network socket. */
      ('private2', c_int),            # int private2;
      ('proto_major_version', c_int), # int proto_major_version;/* major version of server's X protocol */
      ('proto_minor_version', c_int), # int proto_minor_version;/* minor version of servers X protocol */
      ('vendor', c_char_p),           # char *vendor;       /* vendor of the server hardware */
# X.h:71:typedef unsigned long XID;
      ('private3', c_ulong),          #     XID private3;
      ('private4', c_ulong),          # XID private4;
      ('private5', c_ulong),          # XID private5;
      ('private6', c_int),            # int private6;
# XXX NOT SURE
      ('resource_alloc', c_long),     # XID (*resource_alloc)(  /* allocator function */
                                      #     struct _XDisplay*
                                      # );
      ('byte_order', c_int),          # int byte_order;     /* screen byte order, LSBFirst, MSBFirst */
      ('bitmap_unit', c_int),         # int bitmap_unit;    /* padding and data requirements */
      ('bitmap_pad', c_int),          # int bitmap_pad;     /* padding requirements on bitmaps */
      ('bitmap_bit_order', c_int),    # int bitmap_bit_order;   /* LeastSignificant or MostSignificant */
      ('nformats', c_int),            # int nformats;       /* number of pixmap formats in list */
      ('pixmap_format', c_void_p),    # ScreenFormat *pixmap_format;    /* pixmap format list */
      ('private8', c_int),            # int private8;
      ('release', c_int),             # int release;        /* release of the server */
      ('private9', c_void_p),         # struct _XPrivate *private9, *private10;
      ('private10', c_void_p),
      ('qlen', c_int),                # int qlen;       /* Length of input event queue */
      ('last_request_read', c_ulong), # unsigned long last_request_read; /* seq number of last event read */
      ('request', c_long),            # unsigned long request;  /* sequence number of last request. */
# Xlib.h:87:typedef char *XPointer;
      ('private11', c_char_p),        # XPointer private11;
      ('private12', c_char_p),        # XPointer private12;
      ('private13', c_char_p),        # XPointer private13;
      ('private14', c_char_p),        # XPointer private14;
      ('max_request_size', c_uint),   # unsigned max_request_size; /* maximum number 32 bit words in request*/
      ('db', c_void_p),               # struct _XrmHashBucketRec *db;
      ('private15', c_int),           # int (*private15)(
                                      #     struct _XDisplay*
                                      #     );
      ('display_name', c_char_p),     # char *display_name; /* "host:display" string used on this connect*/
      ('default_screen', c_int),      # int default_screen; /* default screen for operations */
      ('nscreens', c_int),            # int nscreens;       /* number of screens on this server*/
      ('screens', c_void_p),          # Screen *screens;    /* pointer to list of screens */
# We do not need the rest
                                      # unsigned long motion_buffer;    /* size of motion buffer */
                                      # unsigned long private16;
                                      # int min_keycode;    /* minimum defined keycode */
                                      # int max_keycode;    /* maximum defined keycode */
                                      # XPointer private17;
                                      # XPointer private18;
                                      # int private19;
                                      # char *xdefaults;    /* contents of defaults from server */
                                      # /* there is more to this structure, but it is private to Xlib */
      ]


class XScreenSaverInfo(Structure):
  _fields_ = [
# X.h:101:typedef XID Window;
# X.h:71:typedef unsigned long XID;
      ('window', c_ulong),            # Window  window;     /* screen saver window - may not exist */
      ('state', c_int),               # int     state;      /* ScreenSaverOff, ScreenSaverOn, ScreenSaverDisabled*/
      ('kind', c_int),                # int     kind;       /* ScreenSaverBlanked, ...Internal, ...External */
      ('til_or_since', c_ulong),      # unsigned long    til_or_since;   /* time til or since screen saver */
      ('idle', c_ulong),              # unsigned long    idle;      /* total time since last user input */
      ('eventMask', c_ulong),         # unsigned long   eventMask; /* currently selected events for this client */
      ]


def get_info(p_display=None, default_root_window=None, p_info=None):

  if p_display is None:
    p_display = _p_display

  if default_root_window is None:
    default_root_window = _default_root_window

  if p_info is None:
    p_info = _p_info

  libXss.XScreenSaverQueryInfo(p_display, default_root_window, p_info)
  return p_info.contents


# Specify return types
libXss.XOpenDisplay.restype = POINTER(Display)
libXss.XScreenSaverAllocInfo.restype = POINTER(XScreenSaverInfo)


_p_display = libXss.XOpenDisplay('')
display = _p_display.contents

# Get DefaultRootWindow(display), which is a macro
# Xlib.h
# #define DefaultRootWindow(dpy)  (ScreenOfDisplay(dpy,DefaultScreen(dpy))->root)
# #define ScreenOfDisplay(dpy, scr)(&((_XPrivDisplay)dpy)->screens[scr])
# #define DefaultScreen(dpy)  (((_XPrivDisplay)dpy)->default_screen)
# ==> I found the following expanding version via Google Code Search
# ==> #define DefaultRootWindow(dpy)  (((dpy)->screens[(dpy)->default_screen]).root)
# Convert display.screens from c_void_p to POINTER(Screen * display.nscreens)
screens = cast(display.screens, POINTER(Screen * display.nscreens))
_default_root_window = screens.contents[display.default_screen].root
_p_info = pointer(XScreenSaverInfo())
del display
del screens


# The following code are copied directly from PyXSS-2.1/xss/__init__.py without
# any modifications.
class IdleTracker:
    """Keeps track of idle times, screensaver state, and tells
    you when you to querying it for the next idle time.  All times
    are in milliseconds.  IdleTracker indicates a change in state when
    your idle time exceeds a certain threshold.  See also XSSTracker."""
    def __init__(self, when_idle_wait=5000, when_disabled_wait=120000,
        idle_threshold=60000):
        """when_idle_wait is the interval at which you should poll when
        you are already idle.  when_disabled_wait is how often you should
        poll if information is unavailable (default: 2 minutes).  
        idle_threshold is the number of seconds of idle time to constitute
        being idle."""
        self.when_idle_wait = when_idle_wait
        self.idle_threshold = idle_threshold
        # we start with a bogus last_state.  this way, the first call to
        # check_idle will report whether we are idle or not.  all subsequent
        # calls will only tell you if the screensaver state has changed
        self.last_state = None
    def check_idle(self):
        """Returns a tuple:
        (state_change, suggested_time_till_next_check, idle_time)
        
        suggested_time_till_next_check and idle_time is in milliseconds.
        state_change is one of:
            None - No change in state
            "idle" - user is idle (idle time is greater than idle threshold)
            "unidle" - user is not idle (idle time is less than idle threshold)
            "disabled" - idle time not available

        Note that "disabled" will be returned every time there is an error."""
        try:
            self.info = get_info()
        except RuntimeError: # XSS can raise a RuntimeError if the
                             # XSS extension cannot be found.
            return ("disabled", self.when_disabled_wait, 0)

        idle = self.info.idle

        if idle > self.idle_threshold: # if we meet the threshold for being
                                       # idle, we are now idle
            current_state = 'idle'
            # we use the standard polling interval
            wait_time = self.when_idle_wait
        else:                          # otherwise, we are not idle
            current_state = 'unidle'
            # wait time is however long it will take for us to go over the 
            # idle threshold
            wait_time = self.idle_threshold - idle

        # check to see if our new state is actually a change
        change = None
        if self.last_state != current_state:
            change = current_state

        self.last_state = current_state
        return (change, wait_time, self.info.idle)

class XSSTracker:
    """Keeps track of idle times, screensaver state, and tells you
    when you to querying it for the next idle time.  All times are
    in milliseconds.  XSSTracker indicates a change in state when your
    screensaver activates.  See also IdleTracker."""
    def __init__(self, when_idle_wait=5000, when_disabled_wait=120000):
        """when_idle_wait is the interval at which you should poll when
        you are already idle.  when_disabled_wait is how often you should
        poll if the screensaver is disabled and you are using XSS for
        your idle threshold.
        
        If you set idle_threshold to 'xss', it will say that your
        threshold for becoming idle is whenever the screensaver activates.
        If you don't use the XScreenSaver extension or otherwise want
        a different idle threshold, you can specify it in milliseconds."""
        self.when_idle_wait = when_idle_wait
        self.when_disabled_wait = when_disabled_wait
        # we start by assuming the screen saver is disabled.  this way, the
        # first call to check_idle will report whether the screensaver is
        # active.  all subsequent calls will only tell you if the screensaver
        # state has changed
        self.last_state = xss.ScreenSaverDisabled
    def check_idle(self):
        """Returns a tuple:
        (state_change, suggested_time_till_next_check, idle_time)
        
        suggested_time_till_next_check and idle_time is in milliseconds.
        state_change is one of:
            None - No change in state
            "idle" - screensaver has turned on since user is now idle
            "unidle" - screensaver has turned off since user is no longer idle
            "disabled" - screensaver is disabled or extension not present

        Note that if the screensaver is disabled, it will return "disabled"
        every time."""
        try:
            self.info = get_info()
        except RuntimeError: # XSS can raise a RuntimeError if the
                             # XSS extension cannot be found.
            return ("disabled", self.when_disabled_wait, 0)

        state = self.info.state

        # if we're disabled, we tell them that. the polling interval for
        # disabledness is when_disabled_wait, which defaults to 2 minutes.
        if state == ScreenSaverDisabled:
            self.last_state = state
            return ("disabled", self.when_disabled_wait, 0)
        
        # wait_time is how long they should wait before polling again.
        if state == ScreenSaverOff:
            # if the screen saver is off, til_or_since will tell us
            # how long it will take to be activated (whether it will
            # be activated depends on whether the user is idle for that
            # period of time)
            wait_time = self.info.til_or_since
        else:
            # otherwise, the screensaver is on.  we don't when we will
            # become unidle, but the when_idle_wait tells us the poll
            # interval (default is 5 seconds)
            wait_time = self.when_idle_wait

        # change is whether or not we have changed.  if we have, we use
        # a string to describe the change
        if state != self.last_state:
            if state == ScreenSaverOff: # if we've changed from On to Off
                                            # they're not idle anymore
                change = 'unidle'
            else:
                change = 'idle' # if we've changed from Off to On, they've gone
                                # idle
        else: # otherwise, they haven't changed state
            change = None

        self.last_state = state
        return (change, wait_time, self.info.idle)

if __name__ == "__main__":
    # this demo shows how you might write a simple poller
    import time
    i = IdleTracker(idle_threshold=5000)
    while 1:
        info = i.check_idle()
        print time.asctime(), info,
        # don't poll more often than 2 seconds
        wait_time = max(info[1] / 1000, 2) 
        print "wait:", wait_time
        time.sleep(wait_time)

