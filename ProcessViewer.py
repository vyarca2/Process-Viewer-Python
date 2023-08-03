import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
import signal
import psutil

procdata = {}
procdatalock = threading.Lock()

def meminfo(pid):

    try:
        process = psutil.Process(pid)
        mem_info = process.memory_info()
        rss_memory = mem_info.rss / (1024 * 1024)  # Convert bytes to MB
        vms_memory = mem_info.vms / (1024 * 1024)  # Convert bytes to MB
        return rss_memory,vms_memory
    
    except psutil.NoSuchProcess:
        return None,None

def procinfo():

    global procdata
    newprocdata = {}

    for proc in psutil.process_iter(['pid','name']):
        pid = proc.info['pid']
        name = proc.info['name']
        rss_memory,vms_memory = procdata.get(pid,(None,None))
        if rss_memory is None or vms_memory is None:
            rss_memory,vms_memory = meminfo(pid)
            with procdatalock:
                procdata[pid] = (name,rss_memory,vms_memory)
        newprocdata[pid] = procdata[pid]

    with procdatalock:
        procdata = newprocdata

    root.after(5000,procinfo)

def proclist():

    selecitem = proctree.selection()
    selecpid = proctree.item(selecitem,"values")[0] if selecitem else None

    for row in proctree.get_children():
        proctree.delete(row)

    with procdatalock:
        for pid, (name,rss_memory,vms_memory) in procdata.items():
            proctree.insert("",'end',values=(pid,name,f"{rss_memory:.2f} MB",f"{vms_memory:.2f} MB"))

    if selecpid:
        for item in proctree.get_children():
            if proctree.item(item,"values")[0] == selecpid:
                proctree.selection_set(item)
                break

    root.after(1000,proclist)

def childproc():

    selecitem = proctree.selection()

    if not selecitem:
        messagebox.showwarning("Warning", "Please select a process to view its child processes.")
        return

    selecpid = int(proctree.item(selecitem,"values")[0])
    childprocs = []

    with procdatalock:
        for proc in psutil.process_iter(['pid','name','ppid']):
            if proc.info['ppid'] == selecpid:
                childprocs.append((proc.info['pid'], proc.info['name']))

    if childprocs:
        childwind = tk.Toplevel(root)
        childwind.title(f"Child Processes - PID: {selecpid}")
        childtree = ttk.Treeview(childwind, columns=("pid","name"), show="headings")
        childtree.heading("pid",text="PID")
        childtree.heading("name",text="Name")
        childtree.pack()

        for pid, name in childprocs:
            childtree.insert("",'end',values=(pid,name))
    else:
        messagebox.showinfo("Info","No child processes found for the selected process.")

def killproc():

    selecitem = proctree.selection()

    if not selecitem:
        messagebox.showwarning("Warning","Please select a process to kill.")
        return

    pid = int(proctree.item(selecitem,"values")[0])

    try:
        os.kill(pid,signal.SIGTERM)
        messagebox.showinfo("Success",f"Process with PID {pid} has been terminated.")
    
    except ProcessLookupError:
        messagebox.showwarning("Warning",f"Process with PID {pid} no longer exists.")
    
    except PermissionError:
        messagebox.showwarning("Warning",f"Access denied to terminate process with PID {pid}.")

def meminfostr():

    virtualmem = psutil.virtual_memory()
    totalmem = virtualmem.total / (1024 * 1024)
    availmem = virtualmem.available / (1024 * 1024)
    return f"Total Memory: {totalmem:.2f} MB\nAvailable Memory: {availmem:.2f} MB"

root = tk.Tk()
root.title("Live Process Monitor")

proctree = ttk.Treeview(root,columns=("pid","name","rss_memory","vms_memory"),show="headings")
proctree.heading("pid",text="PID")
proctree.heading("name",text="Name")
proctree.heading("rss_memory",text="Physical Memory (MB)")
proctree.heading("vms_memory",text="Virtual Memory (MB)")
proctree.pack()

killbutton = tk.Button(root,text="Kill Process",command=killproc)
killbutton.pack()

listchildbutton = tk.Button(root,text="List Child Processes",command=childproc)
listchildbutton.pack()

memory_label = tk.Label(root,text=meminfostr(),anchor="w")
memory_label.pack(fill="x")

fetchthread = threading.Thread(target=procinfo)
fetchthread.daemon = True
fetchthread.start()

root.after(1000,proclist)
root.mainloop()
