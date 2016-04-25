#!/usr/bin/env python3
# Copyright (C) 2016 William Hicks
#
# This file is part of Writing3D.
#
# Writing3D is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

"""A script to simplify installing Writing3D"""

import sys
import site
import platform
import os
import shutil
import fileinput
import zipfile
import tarfile
import subprocess
from urllib.request import urlopen

CURRENT_OS = platform.system()
if CURRENT_OS in ['Darwin']:
    CURRENT_OS = "Mac"
if CURRENT_OS not in ("Linux", "Windows", "Mac"):
    CURRENT_OS = "Other"
try:
    import tkinter as tk
    from tkinter import font
    from tkinter import filedialog
    import tkinter.ttk as ttk
except ImportError:
    if sys.version_info[0] != 3:
        print("Must be run with Python 3.x")
        raw_input()
        raise RuntimeError("Incorrect Python version")

    if CURRENT_OS not in ["Windows", "Mac"]:
        print("Please install tkinter and try again.")
        raw_input()
        raise RuntimeError("tkinter not found")
    else:
        print(
            "tkinter not found on your system. Please contact the Writing3D"
            " maintainer.")
BLENDER_VERSION = "2.76"
IS_64_BIT = sys.maxsize > 2**32
#TODO: Figure out dirs more carefully
BLENDER_DIRS = {
    "Linux": (
        os.path.expandvars(
            "/usr/bin".format(BLENDER_VERSION)
        ),
    ),
    "Mac": (
        os.path.expandvars(
            "/Applications/Blender/"
        ),
    ),
    "Windows": (
        os.path.expandvars(
            "/Applications/Blender/"
        ),
    ),
    "Other": (
        os.path.expanduser("~"),
    )
}

#TODO: Check these
BLENDER_EXECS = {
    "Mac": ("blender", "blenderplayer"),
    "Windows": ("blender.exe", "blenderplayer.exe"),
    "Linux": ("blender", "blenderplayer"),
    "Other": ("blender", "blenderplayer")
}

BASEURL = "http://download.blender.org/release/Blender{}/".format(
    BLENDER_VERSION)

#TODO: No 32 bit versions for Unix-based systems
#TODO: Add check for i686 architecture
#TODO: Add FreeBSD as available OS
DOWNLOAD_URLS = {
    "Linux": (
        "{}blender-{}-linux-glibc211-x86_64.tar.bz2".format(
            BASEURL, BLENDER_VERSION),
        "{}blender-{}-linux-glibc211-x86_64.tar.bz2".format(
            BASEURL, BLENDER_VERSION)
    ),
    "Mac": (
        "{}blender-{}-OSX_10.6-x86_64.zip".format(BASEURL, BLENDER_VERSION),
        "{}blender-{}-OSX_10.6-x86_64.zip".format(BASEURL, BLENDER_VERSION)
    ),
    "Windows": (
        "{}blender-{}-windows32.zip".format(BASEURL, BLENDER_VERSION),
        "{}blender-{}-windows64.zip".format(BASEURL, BLENDER_VERSION)
    )
}

SCRIPTDIR = os.path.abspath(os.path.dirname(__file__))


def module_dir():
    for root, dirs, files in os.walk(site.USER_BASE):
        if "site-packages" in dirs:
            return os.path.abspath(os.path.join(root, "site-packages"))

def blender_module_dir(blender_directory):
    cur_path = blender_directory
    for elem in ["addons", "modules"]:
        for root, dirs, files in os.walk(cur_path):
            if elem in dirs:
                cur_path = os.path.join(root, elem)
                break
    return cur_path


def copy_module_for_blender(blender_dir):
    sys_dir = module_dir()
    for filename in os.listdir(sys_dir):
        if (
                filename.startswith("Writing3D") and
                os.path.splitext(filename)[1].lower() == ".egg"):
            egg_path = os.path.join(sys_dir, filename)
            break
    shutil.copy(egg_path, blender_module_dir(blender_dir))


def warn(message):
    warn_window = tk.Toplevel()
    warn_window.title("ERROR")
    error_message = tk.Message(warn_window, text=message, width=200)
    error_message.pack()
    dismiss = tk.Button(
        warn_window, text="Dismiss", command=warn_window.destroy)
    dismiss.pack()


def modify_paths():
    for root, dirs, files in os.walk(os.path.join(SCRIPTDIR, "samples")):
        for file_ in files:
            if os.path.splitext(file_)[1].lower() == ".py":
                for line in fileinput.input(os.path.join(root, file_), inplace=1):
                    if "PATHSUBTAG" in line:
                        print("sys.path.append(r'{}')  # PATHSUBTAG".format(
                            module_dir()))
                    else:
                        print(line, end="")


class Installer(tk.Frame):
    """GUI installer for Writing3D"""

    def choose_install_directory(self):
        if (
                self.install_directory is not None and
                os.path.exists(self.install_directory)):
            directory = self.install_directory
        else:
            directory = os.path.expanduser("~")
        directory = filedialog.askdirectory(
            title="Install directory",
            initialdir=directory
        )
        directory = os.path.abspath(directory)
        install_directory = os.path.join(directory, "Writing3D")
        if not os.path.exists(install_directory):
            os.makedirs(install_directory)
            #TODO: Handle failure to make install directory
        self.install_directory = install_directory
        if self.install_directory is not None:
            self.next_button.config(state=tk.NORMAL)

    def use_old_blender(self):
        default_directories = BLENDER_DIRS[CURRENT_OS]
        blender_directory = os.path.expanduser("~")
        for directory in default_directories:
            if os.path.exists(directory):
                blender_directory = directory
                break
        blender_directory = filedialog.askopenfilename(
            title="Select Blender Executable",
            initialdir=blender_directory
        )
        self.blender_directory = os.path.dirname(blender_directory)
        if self.blender_directory is not None:
            self.next_button.config(state=tk.NORMAL)

    def download_blender(self):
        chunk = self.url_response.read(16*1024)
        if chunk:
            self.download_file.write(chunk)
            self.progress.step(16/1024.)
            self.after(1, self.download_blender)
        else:
            self.download_file.close()
            self.install_blender()

    def start_blender_install(self):
        self.next_button.config(state=tk.DISABLED)
        self.progress = ttk.Progressbar(
            self.interior, orient="horizontal", mode="indeterminate"
        )
        self.progress.pack(expand=1, fill=tk.X, side=tk.BOTTOM)
        os.chdir(self.install_directory)
        #TODO: This is ugly
        self.downloading = True
        self.url_response = urlopen(DOWNLOAD_URLS[CURRENT_OS][IS_64_BIT])
        if CURRENT_OS in ("Linux", "Other"):
            self.download_filename = os.path.join(
                self.install_directory, "blender.tar.bz2")
        else:
            self.download_filename = os.path.join(
                self.install_directory, "blender.zip")
        self.download_file = open(self.download_filename, 'wb')
        self.after(1, self.download_blender)

    def install_blender(self):
        filename = self.download_filename
        if CURRENT_OS in ("Linux", "Other"):
            with tarfile.open(filename, "r:bz2") as install_file:
                self.blender_directory = os.path.join(
                    self.install_directory, "blender",
                    install_file.next().name)
                install_file.extractall(path="blender")
        else:
            with zipfile.ZipFile(filename) as install_file:
                self.blender_directory = os.path.join(
                    self.install_directory, "blender",
                    install_file.namelist()[0])
                install_file.extractall(path="blender")
        if self.blender_directory is not None:
            self.next_button.config(state=tk.NORMAL)
        self.progress.destroy()
        self.next_slide()

    def install_w3d(self):
        progress = ttk.Progressbar(
            self.interior, orient="horizontal", mode="indeterminate"
        )
        progress.pack(expand=1, fill=tk.X, side=tk.BOTTOM)
        progress.start(50)

        self.next_button.config(state=tk.DISABLED)
        self.writer_script_location = os.path.join(
            SCRIPTDIR, "w3d_writer.py")
        blender_exec_path = os.path.join(
            self.blender_directory,
            BLENDER_EXECS[CURRENT_OS][0]
        )
        bplay_exec_path = os.path.join(
            self.blender_directory,
            BLENDER_EXECS[CURRENT_OS][1]
        )
        if not os.path.exists(blender_exec_path):
            for root, dirs, files in os.walk(self.blender_directory):
                if BLENDER_EXECS[CURRENT_OS][0] in files:
                    blender_exec_path = os.path.join(
                        root, BLENDER_EXECS[CURRENT_OS][0])
                if BLENDER_EXECS[CURRENT_OS][1] in files:
                    bplay_exec_path = os.path.join(
                        root, BLENDER_EXECS[CURRENT_OS][1])
        init_filename = os.path.join(
            SCRIPTDIR, "pyw3d", "__init__.py")
        new_init_filename = 'tmp_init.py'
        #TODO: Use fileinput
        with open(init_filename) as init_file:
            with open(new_init_filename, 'w') as new_init_file:
                for line in init_file:
                    if "BLENDEREXECSUBTAG" in line:
                        new_init_file.write(
                            "BLENDER_EXEC = r'{}'".format(blender_exec_path)
                        )
                        new_init_file.write("  # BLENDEREXECSUBTAG\n")
                    elif "BLENDERPLAYERSUBTAG" in line:
                        new_init_file.write(
                            "BLENDER_PLAY = r'{}'".format(bplay_exec_path)
                        )
                        new_init_file.write("  # BLENDERPLAYERSUBTAG\n")
                    else:
                        new_init_file.write(line)
        shutil.move(new_init_filename, init_filename)
        modify_paths()

        os.chdir(SCRIPTDIR)
        subprocess.call([
            sys.executable, "setup.py", 'install', '--user']
        )
        if CURRENT_OS in ("Windows", "Mac"):
            copy_module_for_blender(self.blender_directory)
        progress.destroy()
        self.next_button.config(state=tk.NORMAL)
        self.next_slide()

    def init_slide(self):
        self.interior.destroy()
        self.interior = tk.Frame(self)
        self.interior.pack(anchor=tk.N, fill=tk.BOTH, expand=1)
        self.create_buttons()
        if self.current_slide == 0:
            self.label = tk.Label(
                self.interior,
                text="""Welcome to Writing3D!

This installer will help guide you through the process
of setting up Writing3D and Blender, the engine used to
render Writing3D projects.

Please click the Next button to begin the install process.""",
                font=self.font,
                justify=tk.LEFT)
            self.label.pack()
            return

        if self.current_slide == 1:
            self.label = tk.Label(
                self.interior,
                text="""Select an Install Directory

First, choose where you would like to install Writing3D by
clicking the "Choose Install Directory" button. Then click
Next.""",
                font=self.font,
                justify=tk.LEFT)
            self.label.pack()
            if self.install_directory is None:
                self.next_button.config(state=tk.DISABLED)
            self.choose_dir = tk.Button(
                self.interior, text="Choose Install Directory",
                command=self.choose_install_directory)
            self.choose_dir.pack(expand=1, fill=tk.X)
            return

        if self.current_slide == 2:
            self.label = tk.Label(
                self.interior,
                text="""Installing Blender

Next, let's set up Blender. If you already have Blender
installed and would like to use the previously-installed
version, please click "Use Installed Version" Otherwise,
select "Install Blender Now."

Note: It may take several minutes to download and install
Blender, depending on your network connection. Please wait.

Please click the Next button to begin the install process.""",
                font=self.font,
                justify=tk.LEFT)
            self.label.pack()
            self.use_old_button = tk.Button(
                self.interior, text="Use Installed Version",
                command=self.use_old_blender)
            self.install_blender_button = tk.Button(
                self.interior, text="Install Blender Now",
                command=self.start_blender_install)
            self.use_old_button.pack(fill=tk.X, expand=1)
            self.install_blender_button.pack(fill=tk.X, expand=1)
            if self.blender_directory is None:
                self.next_button.config(state=tk.DISABLED)
            return

        if self.current_slide == 3:
            self.label = tk.Label(
                self.interior,
                text="""Installing Writing3D

Please wait.""",
                font=self.font,
                justify=tk.LEFT)
            self.label.pack()
            self.install_w3d()
            return

        if self.current_slide == 4:
            self.label = tk.Label(
                self.interior,
                text="""Finished!

Writing3D has been successfully installed. Please visit
https://wphicks.github.io/Writing3D/
for information on how to get started creating VR
projects.

""",
                font=self.font,
                justify=tk.LEFT)
            self.label.pack()
            self.create_finish_button()
            return

    def next_slide(self):
        self.current_slide = min(
            self.current_slide + 1,
            self.total_slides - 1)
        self.init_slide()

    def back_slide(self):
        self.current_slide = max(self.current_slide - 1, 0)
        self.init_slide()

    def create_finish_button(self):
        self.next_button.destroy()
        self.finish_button = tk.Button(
            self.interior, text="Finish", command=self.parent.destroy)
        self.finish_button.pack(
            side=tk.RIGHT, anchor=tk.SE, fill=tk.X, expand=1)

    def create_buttons(self):
        #TODO: This is an ugly hack
        try:
            self.back_button.destroy()
            self.next_button.destroy()
        except AttributeError:
            pass
        self.back_button = tk.Button(
            self, text="Back", command=self.back_slide)
        if self.current_slide == 0:
            self.back_button.config(state=tk.DISABLED)
        self.next_button = tk.Button(
            self, text="Next", command=self.next_slide)
        if self.current_slide == self.total_slides - 1:
            self.next_button.config(state=tk.DISABLED)
        self.back_button.pack(side=tk.LEFT, anchor=tk.SW, fill=tk.X, expand=1)
        self.next_button.pack(side=tk.RIGHT, anchor=tk.SE, fill=tk.X, expand=1)

    def initUI(self):
        self.parent.title("W3D Installer")
        self.pack(fill=tk.BOTH, expand=1)
        self.interior = tk.Frame(self)
        self.init_slide()
        self.create_buttons()

    def __init__(self, parent):
        super(Installer, self).__init__(parent)
        self.parent = parent
        self.current_slide = 0
        self.total_slides = 5
        self.install_directory = None
        self.blender_directory = None
        self.downloading = True
        self.font = font.Font(family="Helvetica", size=14)
        self.initUI()


def start_installer():
    root = tk.Tk()
    #width = root.winfo_screenwidth()
    #height = root.winfo_screenheight()
    #root.geometry("{}x{}".format(width, height))
    Installer(root)
    root.mainloop()

if __name__ == "__main__":
    start_installer()
