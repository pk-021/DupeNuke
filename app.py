import tkinter as tk
import os
from tkinter import filedialog
from  ttkbootstrap import Style
import ttkbootstrap as ttk
from PIL import Image, ImageTk
import detect


class MyGUI():
    def __init__(self):    
        self.root = tk.Tk()
        self.root.geometry("1200x1000")
        style = Style(theme='solar')
        self.selected_path = str()
        self.images = []
        self.vars = []
        self.include_subfolders = ttk.BooleanVar()
        
        
        action_frm = ttk.Frame(self.root)
        action_frm.pack(pady=10)

        
        self.get_folder_btn = ttk.Button(action_frm,bootstyle= "light", command= self.get_folder,text="No folder selected.",width=100)
        self.get_folder_btn.grid(row=0,column=0)
        
        self.process_btn = ttk.Button(action_frm,command=self.process_folder,text= "GO!")
        self.process_btn.grid(row=0,column=1)
        
        self.include_subfolders_chkbox = ttk.Checkbutton(
            action_frm,
            text = "include subfolders",
            variable=self.include_subfolders,
            onvalue= True,
            offvalue= False,
        )
        self.include_subfolders_chkbox.grid(row=1,column=0,pady=10)
        
        canvas_frm = ttk.Frame(self.root)
        canvas_frm.pack(fill="both",expand=True,padx=100)
        
        canvas = ttk.Canvas(canvas_frm)
        scrollBar = ttk.Scrollbar(canvas_frm,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollBar.set)
        
        scrollBar.pack(side="right",fill="y")
        canvas.pack(side="left",fill="both",expand=True) 
        
        self.photo_frm = ttk.Frame(canvas)    
        self.photo_frm.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )        
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
             
        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # For Windows
        
        canvas.create_window((0, 0), window=self.photo_frm, anchor="nw")
        
        self.del_btn = ttk.Button(self.root,text="DELETE",command=self.delete_selected,bootstyle="danger")
        self.del_btn.pack(anchor="s",pady=50)
        
        self.root.mainloop()
        

            
    def process_folder(self):
        try:
            near_duplicates = detect.find_near_duplicates(self.selected_path, 0.7, 16, 16,include_SubFolders=self.include_subfolders.get())
            if near_duplicates:
                print(f"Found {len(near_duplicates)} near-duplicate images in (threshold)")
                # for a,b,s in near_duplicates:
                #     print(f"{s:.2%} similarity: file 1: {a} - file 2: {b}")
                groups = detect.group_similar_images(near_duplicates)
                self.render_images(groups)
            else:
                print(f"No near-duplicates found in {self.selected_path} (threshold)")
        except OSError:
            print(f"Couldn't open input directory {self.selected_path}")
            
        
                    
    def get_folder(self):
        path = filedialog.askdirectory(title="Select a folder")
        if path:
            self.get_folder_btn.config(text=path)
            self.selected_path = path
            
    def render_images(self, image_groups):
        self.clear_gallery()

        for group in image_groups:
            group_frm = ttk.Frame(self.photo_frm,relief='solid')
            group_frm.pack(fill='x', anchor='w')

            num_per_row = 5
            row_frm = None

            for i, path in enumerate(group):
                if i % num_per_row == 0:
                    row_frm = ttk.Frame(group_frm)
                    row_frm.pack(fill='x', anchor='w', pady=5)

                img = Image.open(path)
                img.thumbnail((200, 200))
                img_tk = ImageTk.PhotoImage(img)
                self.images.append((img_tk,path))  # Prevent garbage collection

                var = tk.BooleanVar()
                self.vars.append(var)

                frame = ttk.Frame(row_frm, padding=10, relief="solid", borderwidth=2)
                frame.pack(side='left', padx=5)
                
                infobox = ttk.Frame(frame)
                chk = tk.Checkbutton(infobox, variable=var)
                chk.grid(row=0, column=0)
                path_label = ttk.Label(infobox,text=path.split('\\')[-1])
                path_label.grid(row = 0, column= 1,sticky="ew")
                
                infobox.pack(anchor="n")

                lbl = tk.Label(frame, image=img_tk)
                lbl.pack()
                
                def toggle(var=var):
                    var.set(not var.get())
                    
                frame.bind("<Button-1>", lambda e, v=var: toggle(v))
                lbl.bind("<Button-1>", lambda e, v=var: toggle(v))
                
                
    def clear_gallery(self):
        for widget in self.photo_frm.winfo_children():
            widget.destroy()
        self.images.clear()
        self.vars.clear()    

    def delete_selected(self):
        for image, var in zip(self.images, self.vars):
            path = image[1]
            if var.get():
                print("delete ",path)
                os.remove(path) 
                
        self.process_folder()      
        
        
gui = MyGUI()