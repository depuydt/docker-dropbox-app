"""Syncronization system for APP Dropbox.

Starting point from [1] Use API v2.

[1] https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py
"""

from __future__ import print_function

import argparse
import contextlib
import os, sys, time, logging, datetime
import six
import unicodedata
# How it is work watchdog
# * https://pythonhosted.org/watchdog/quickstart.html#a-simple-example
# * https://stackoverflow.com/questions/32923451/how-to-run-an-function-when-anything-changes-in-a-dir-with-python-watchdog
# * https://stackoverflow.com/questions/46372041/seeing-multiple-events-with-python-watchdog-library-when-folders-are-created
from watchdog.observers import Observer
#from watchdog.events import LoggingEventHandler
from watchdog.events import PatternMatchingEventHandler
# Colored terminal - https://pypi.org/project/termcolor/
from termcolor import colored, cprint

if sys.version.startswith('2'):
    input = raw_input  # noqa: E501,F821; pylint: disable=redefined-builtin,undefined-variable,useless-suppression

import dropbox

# OAuth2 access token.
TOKEN = os.environ['DROPBOX_TOKEN'] if "DROPBOX_TOKEN" in os.environ else ""
FOLDER = os.environ['DROPBOX_FOLDER'] if "DROPBOX_FOLDER" in os.environ else "Downloads"
ROOTDIR = os.environ['DROPBOX_ROOTDIR'] if "DROPBOX_ROOTDIR" in os.environ else "~/Downloads"

class UpDown(PatternMatchingEventHandler):

    def __init__(self, token, folder, rootdir, verbose=False):
        super(UpDown, self).__init__(ignore_patterns=["*.swp"])
        self.folder = folder
        self.rootdir = rootdir
        self.verbose = verbose
        if verbose:
            print('Dropbox folder name:', folder)
            print('Local directory:', rootdir)
        self.dbx = dropbox.Dropbox(token)
        
    def getFolderAndFile(self, src_path):
        abs_path = os.path.dirname(src_path)
        subfolder = os.path.relpath(abs_path, self.rootdir)
        subfolder = subfolder if subfolder != "." else "" 
        name = os.path.basename(src_path)
        return subfolder, name
        
    def on_moved(self, event):
        subfolder, src_name = self.getFolderAndFile(event.src_path)
        _, dest_name = self.getFolderAndFile(event.dest_path)
        print("Moved", src_name, "->", dest_name, "in folder", subfolder)
        self.move(subfolder, src_name, dest_name)
    
    def on_created(self, event):
        subfolder, name = self.getFolderAndFile(event.src_path)
        print("Created", name, "in folder", subfolder)
        self.upload(event.src_path, subfolder, name)
        
    def on_deleted(self, event):
        subfolder, name = self.getFolderAndFile(event.src_path)
        print("Deleted", name, "in folder", subfolder)
        self.delete(subfolder, name)
        
    def on_modified(self, event):
        if not event.is_directory:
            subfolder, name = self.getFolderAndFile(event.src_path)
            print("Modified", name, "in folder", subfolder)
            # Syncronization from Local to Dropbox
            self.upload(event.src_path, subfolder, name, overwrite=True)
        
    def sync(self, option="default"):
        """ Sync from dropbox to Local and viceversa
        """
        if os.listdir(self.rootdir):
            self.syncFromLocal(option="no")
        else:
            print("Folder", self.rootdir, "is empty")
        self.syncFromDropBox()

    def storefile(self, res, filename, timedb):
        out = open(filename, 'wb')
        out.write(res)
        out.close()
        # Fix time with md time
        # https://nitratine.net/blog/post/change-file-modification-time-in-python/
        modTime = time.mktime(timedb.timetuple())
        os.utime(filename, (modTime, modTime))
                
    def syncFromDropBox(self, subfolder=""):
        """ Recursive function to download all files from dropbox
        """
        listing = self.list_folder(subfolder)
        for nname in listing:
            md = listing[nname]
            if (isinstance(md, dropbox.files.FileMetadata)):
                path = self.rootdir + subfolder + "/" + nname
                res = self.download(subfolder, nname)
                # Store file in folder
                if os.path.exists(path):
                    mtime = os.path.getmtime(path)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(path)
                    if(mtime_dt == md.client_modified and size == md.size):
                        print(nname, 'is already synced [stats match]')
                    else:
                        self.storefile(res, path, md.client_modified)
                else:
                    self.storefile(res, path, md.client_modified)
            if (isinstance(md, dropbox.files.FolderMetadata)):
                path = self.rootdir + subfolder + "/" + nname
                if self.verbose: print('Descending into', nname, '...')
                if not os.path.exists(path):
                    os.makedirs(path)
                self.syncFromDropBox(subfolder=subfolder + "/" + nname)

    def syncFromLocal(self):

        for dn, dirs, files in os.walk(self.rootdir):
            subfolder = dn[len(self.rootdir):].strip(os.path.sep)
            listing = self.list_folder(subfolder)
            if self.verbose: print('Descending into', subfolder, '...')

            # First do all the files.
            for name in files:
                fullname = os.path.join(dn, name)
                print("fullname:", fullname)
                print("subfolder:", subfolder, "- name:", name)
                if not isinstance(name, six.text_type):
                    name = name.decode('utf-8')
                nname = unicodedata.normalize('NFC', name)
                if name.startswith('.'):
                    print('Skipping dot file:', name)
                elif name.startswith('@') or name.endswith('~'):
                    print('Skipping temporary file:', name)
                elif name.endswith('.pyc') or name.endswith('.pyo'):
                    print('Skipping generated file:', name)
                elif nname in listing:
                    md = listing[nname]
                    mtime = os.path.getmtime(fullname)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(fullname)
                    if (isinstance(md, dropbox.files.FileMetadata) and
                            mtime_dt == md.client_modified and size == md.size):
                        print(name, 'is already synced [stats match]')
                    else:
                        print(name, 'exists with different stats, downloading')
                        res = self.download(subfolder, name)
                        with open(fullname) as f:
                            data = f.read()
                        if res == data:
                            print(name, 'is already synced [content match]')
                        else:
                            print(name, 'has changed since last sync')
                            # Overwrite old files
                            self.upload(fullname, subfolder, name, overwrite=True)
                # Upload all new files
                self.upload(fullname, subfolder, name)

            # Then choose which subdirectories to traverse.
            keep = []
            for name in dirs:
                if name.startswith('.'):
                    print('Skipping dot directory:', name)
                elif name.startswith('@') or name.endswith('~'):
                    print('Skipping temporary directory:', name)
                elif name == '__pycache__':
                    print('Skipping generated directory:', name)
                elif self.yesno('Descend into %s' % name, True, option):
                    print('Keeping directory:', name)
                    keep.append(name)
                else:
                    print('OK, skipping directory:', name)
            dirs[:] = keep

    def list_folder(self, subfolder, recursive=False):
        """List a folder.

        Return a dict mapping unicode filenames to
        FileMetadata|FolderMetadata entries.
        """
        path = '/%s/%s' % (self.folder, subfolder.replace(os.path.sep, '/'))
        while '//' in path:
            path = path.replace('//', '/')
        path = path.rstrip('/')
        try:
            with self.stopwatch('list_folder'):
                res = self.dbx.files_list_folder(path, recursive=recursive)
        except dropbox.exceptions.ApiError as err:
            if self.verbose: print('Folder listing failed for', path, '-- assumed empty:', err)
            return {}
        else:
            rv = {}
            for entry in res.entries:
                rv[entry.name] = entry
            return rv

    def move(self, subfolder, src_name, dest_name):
        """ Move file or folder from dropbox.
        Return True if is moved from dropbox
        """
        src_path = self.normalizePath(subfolder, src_name)
        dest_path = self.normalizePath(subfolder, dest_name)
        with self.stopwatch('delete'):
            try:
                md = self.dbx.files_move(src_path, dest_path)
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return False
        return True
    
    def delete(self, subfolder, name):
        """ Delete a file from dropbox.
        Return True if is fully delete from dropbox
        """
        path = self.normalizePath(subfolder, name)
        with self.stopwatch('delete'):
            try:
                md = self.dbx.files_delete(path)
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return False
        return True

    def download(self, subfolder, name):
        """Download a file.
        Return the bytes of the file, or None if it doesn't exist.
        """
        path = self.normalizePath(subfolder, name)
        with self.stopwatch('download'):
            try:
                md, res = self.dbx.files_download(path)
            except dropbox.exceptions.HttpError as err:
                print('*** HTTP error', err)
                return None
        data = res.content
        if self.verbose: print(len(data), 'bytes; md:', md)
        return data
        
    def createFolder(self, fullname, subfolder, name):
        path = self.normalizePath(subfolder, name)
        self.dbx.files_create_folder(path)

    def upload(self, fullname, subfolder, name, overwrite=False):
        """Upload a file.
        Return the request response, or None in case of error.
        """
        path = self.normalizePath(subfolder, name)
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(fullname)
        if os.path.isdir(fullname):
            res = self.dbx.files_create_folder(path)
        else:
            with open(fullname, 'rb') as f:
                data = f.read()
            with self.stopwatch('upload %d bytes' % len(data)):
                try:
                    res = self.dbx.files_upload(
                        data, path, mode,
                        client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                        mute=True)
                except dropbox.exceptions.ApiError as err:
                    print('*** API error', err)
                    return None
            if self.verbose: print('uploaded as', res.name.encode('utf8'))
        return res

    def normalizePath(self, subfolder, name):
        """ Normalize folder for Dropbox syncronization.
        """
        path = '/%s/%s/%s' % (self.folder, subfolder.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        return path

    @contextlib.contextmanager
    def stopwatch(self, message):
        """Context manager to print how long a block of code took."""
        t0 = time.time()
        try:
            yield
        finally:
            t1 = time.time()
            if self.verbose: print('Total elapsed time for %s: %.3f' % (message, t1 - t0))


if __name__ == '__main__':
    """Main program.

    Parse command line, then iterate over files and directories under
    rootdir and upload all files.  Skips some temporary files and
    directories, and avoids duplicate uploads by comparing size and
    mtime with the server.
    """
    #logging.basicConfig(level=logging.INFO,
    #                    format='%(asctime)s - %(message)s',
    #                    datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(description='Sync ~/dropbox to Dropbox')
    parser.add_argument('folder', nargs='?', default=FOLDER,
                        help='Folder name in your Dropbox')
    parser.add_argument('rootdir', nargs='?', default=ROOTDIR,
                        help='Local directory to upload')
    parser.add_argument('--token', default=TOKEN,
                        help='Access token '
                        '(see https://www.dropbox.com/developers/apps)')
    parser.add_argument('--fromDropbox', '-db', action='store_true',
                        help='Syncronize from Dropbox first')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show all Take default answer on all questions')
    # Parser arguments
    args = parser.parse_args()
    if not args.token:
        print('--token is mandatory')
        sys.exit(2) 
            
    folder = args.folder
    rootdir = os.path.expanduser(args.rootdir)
    if not os.path.exists(rootdir):
        print(rootdir, 'does not exist on your filesystem')
        sys.exit(1)
    elif not os.path.isdir(rootdir):
        print(rootdir, 'is not a folder on your filesystem')
        sys.exit(1)
    # Start updown sync        
    updown = UpDown(args.token, folder, rootdir, args.verbose)
    
    updown.syncFromLocal()
    
    # Initialize file and folder observer
    observer = Observer()
    observer.schedule(updown, rootdir, recursive=True)
    
    print("DropboxSync [{}]".format(colored("START", "green")))
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
# EOF
