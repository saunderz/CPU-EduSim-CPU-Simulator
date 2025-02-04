import tkinter as tk
import time
from tkinter import font
import matplotlib.pyplot as plt
import ctypes
import os

lib_name = "cpu_backend.dll" #Compilação do backend
backend = ctypes.CDLL(os.path.join(os.path.dirname(__file__), lib_name))

# --------------- Declarações das funções do backend ---------------
backend.initCPU.argtypes = []
backend.initCPU.restype  = None

backend.resetCPU.argtypes = []
backend.resetCPU.restype  = None

backend.nextInstruction.argtypes = []
backend.nextInstruction.restype  = None

backend.loadDefaultInstructions.argtypes = []
backend.loadDefaultInstructions.restype  = None

backend.setInstructions.argtypes = [ctypes.POINTER(ctypes.c_char_p), ctypes.c_int]
backend.setInstructions.restype  = None

backend.getRegistersString.argtypes = []
backend.getRegistersString.restype  = ctypes.c_char_p

backend.getMemoryString.argtypes = []
backend.getMemoryString.restype  = ctypes.c_char_p

backend.setMemoryValue.argtypes = [ctypes.c_int, ctypes.c_int]
backend.setMemoryValue.restype  = None

backend.getMemoryValue.argtypes = [ctypes.c_int]
backend.getMemoryValue.restype  = ctypes.c_int

backend.getMemorySize.argtypes = []
backend.getMemorySize.restype  = ctypes.c_int

backend.getExplanationMode.argtypes = []
backend.getExplanationMode.restype  = ctypes.c_int

backend.setExplanationMode.argtypes = [ctypes.c_int]
backend.setExplanationMode.restype  = None

backend.getLastOperationText.argtypes = []
backend.getLastOperationText.restype  = ctypes.c_char_p

backend.getLastExplanationText.argtypes = []
backend.getLastExplanationText.restype  = ctypes.c_char_p

backend.getTotalCycles.argtypes = []
backend.getTotalCycles.restype  = ctypes.c_int

backend.clearHistory.argtypes = []
backend.clearHistory.restype  = None

backend.getHistoryString.argtypes = []
backend.getHistoryString.restype  = ctypes.c_char_p

backend.getLastInstructionCost.argtypes = []
backend.getLastInstructionCost.restype  = ctypes.c_int

backend.getCacheStatus.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
backend.getCacheStatus.restype  = None

backend.setCacheLineData.argtypes = [ctypes.c_int, ctypes.c_int]
backend.setCacheLineData.restype  = None

backend.getCacheLineString.argtypes = [ctypes.c_int]
backend.getCacheLineString.restype  = ctypes.c_char_p

backend.getCacheSize.argtypes = []
backend.getCacheSize.restype  = ctypes.c_int

backend.setRegisterValue.argtypes = [ctypes.c_char_p, ctypes.c_int]
backend.setRegisterValue.restype  = None

backend.getInstructionCount.argtypes = []
backend.getInstructionCount.restype  = ctypes.c_int

backend.getInstructionLine.argtypes = [ctypes.c_int]
backend.getInstructionLine.restype  = ctypes.c_char_p

# Mapeamento
backend.setCacheMappingMode.argtypes = [ctypes.c_int]
backend.setCacheMappingMode.restype  = None
backend.getCacheMappingMode.argtypes = []
backend.getCacheMappingMode.restype  = ctypes.c_int

class CPUVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulação de CPU - Mapeamento na Primeira Linha (Direita)")
        self.root.geometry("1920x1080")

        self.large_font  = font.Font(family="Arial", size=17, weight="bold")
        self.medium_font = font.Font(family="Arial", size=14)

        # Canvas principal
        self.canvas = tk.Canvas(self.root, width=1600, height=800, bg="white")
        self.canvas.grid(row=0, column=0, columnspan=5, padx=10, pady=10)

        # Unidade de Controle
        self.control_box = self.canvas.create_rectangle(500,50,950,150, fill="lightblue", tags="control")
        self.canvas.create_text(725,100, text="Unidade de Controle", font=self.large_font, tags="control_text")
        self.control_button = tk.Button(
            self.root,text="?",font=self.medium_font,
            command=lambda: self.show_component_info("Unidade de Controle","Gerencia e coordena as operações.")
        )
        self.control_button.place(x=495,y=45)

        # ALU
        self.alu_box = self.canvas.create_rectangle(500,200,950,300, fill="lightgreen", tags="alu")
        self.canvas.create_text(725,250, text="ALU", font=self.large_font, tags="alu_text")
        self.alu_button = tk.Button(
            self.root,text="?",font=self.medium_font,
            command=lambda: self.show_component_info("ALU","Executa operações aritméticas e lógicas.")
        )
        self.alu_button.place(x=495,y=195)

        # Registradores
        self.register_names = ["R1","R2","R3","R4"]
        self.register_boxes = {}
        for i, reg in enumerate(self.register_names):
            x1,y1 = 100, 50 + i*120
            x2,y2 = 400, 150 + i*120
            box_id = self.canvas.create_rectangle(x1,y1,x2,y2, fill="lightyellow", tags=reg)
            text_id= self.canvas.create_text((x1+x2)//2,(y1+y2)//2, text=f"{reg}: 0", font=self.large_font)
            self.register_boxes[reg] = (box_id, text_id)
            b = tk.Button(
                self.root,text="?",font=self.medium_font,
                command=lambda r=reg:self.show_component_info(r,"Armazena dados temporários.")
            )
            b.place(x=95,y=45 + i*120)

        # Cache
        self.cache_box = self.canvas.create_rectangle(500,400,950,600, fill="lightcyan", tags="cache")
        self.canvas.create_text(725,380,text="Memória Cache", font=self.large_font)
        self.cache_button = tk.Button(
            self.root, text="?", font=self.medium_font,
            command=lambda: self.show_component_info(
                "Cache",
                "Memória mais rápida e menor que a principal,\n"
                "usada para acelerar o acesso (4 linhas).\n"
                "Mapeamento Direto ou Associativo.\n\n"
                "V=Valid, T=Tag, D=Data"
            )
        )
        self.cache_button.place(x=500, y=400)

        self.cache_size = backend.getCacheSize()
        self.cache_labels = []
        for i in range(self.cache_size):
            label_id = self.canvas.create_text(715, 420 + i*50, text="", font=self.medium_font)
            self.cache_labels.append(label_id)

        # Memória Principal
        self.memory_box = self.canvas.create_rectangle(1100,50,1350,600, fill="lightgray", tags="memory")
        self.canvas.create_text(1225,25, text="Memória Principal (RAM)", font=self.large_font)
        self.memory_button = tk.Button(
            self.root, text="?", font=self.medium_font,
            command=lambda: self.show_component_info("Memória","Armazena 10 posições de dados.")
        )
        self.memory_button.place(x=1095,y=45)

        self.memory_labels = []
        mem_size = backend.getMemorySize()
        for i in range(mem_size):
            lbl_id = self.canvas.create_text(1225,70 + i*50, text=f"[{i}]: 0", font=self.large_font)
            self.memory_labels.append(lbl_id)

        # Box Vermelho (Esforço Computacional)
        self.computation_box = self.canvas.create_rectangle(500,670,950,760, outline="red", width=3, tags="computation_box")
        self.computation_info_button = tk.Button(
            self.root, text="?", font=self.medium_font,
            command=lambda: self.show_component_info(
                "Ciclos de Clock",
                "LOAD/STORE(HIT)=5\nLOAD/STORE(MISS)=10\nADD/SUB=2\nReflete custo de HIT/MISS."
            )
        )
        self.computation_info_button.place(x=500, y=660)

        self.total_cycles_label = tk.Label(self.root,text="Ciclos de Clock (Total): 0", font=self.medium_font)
        self.total_cycles_label.place(x=625,y=700)
        self.current_cost_label = tk.Label(self.root,text="Custo da Instrução Atual: 0", font=self.medium_font)
        self.current_cost_label.place(x=625,y=730)

        # Cache Status
        self.cache_status_label = tk.Label(self.root, text="Cache Hits: 0 | Misses: 0", font=self.medium_font)
        self.cache_status_label.place(x=610, y=620)

        # Botões no topo (linha 1)
        self.next_button = tk.Button(self.root, text="Próxima Instrução", font=self.medium_font, command=self.next_instruction)
        self.next_button.grid(row=1, column=0, pady=10, padx=10)

        self.explanation_mode = False
        self.explanation_button = tk.Button(
            self.root,
            text="Modo Explicação: Desativado",
            font=self.medium_font,
            command=self.toggle_explanation
        )
        self.explanation_button.grid(row=1, column=1, pady=10, padx=10)

        self.reset_button = tk.Button(self.root, text="Resetar", font=self.medium_font, command=self.reset)
        self.reset_button.grid(row=1, column=2, pady=10, padx=10)

        self.mapping_var = tk.StringVar(value="Direto")
        if backend.getCacheMappingMode() == 1:
            self.mapping_var.set("Associativo")

        # Cria OptionMenu
        self.mapping_menu = tk.OptionMenu(
            self.root,
            self.mapping_var,
            "Direto",
            "Associativo",
            command=self.update_mapping_mode
        )
        self.mapping_menu.config(font=self.medium_font)

        # Label do Mapeamento (coluna 3), OptionMenu (coluna 4)
        self.mapping_label = tk.Label(self.root, text="Mapeamento da Cache:", font=self.medium_font)
        self.mapping_label.grid(row=1, column=3, sticky="e", padx=5)
        self.mapping_menu.grid(row=1, column=4, padx=10, pady=10)

        # Demais botões
        self.history_button = tk.Button(self.root,text="Exibir Histórico",font=self.medium_font,command=self.show_history)
        self.history_button.grid(row=3,column=1,pady=10, padx=10)

        self.edit_memory_button = tk.Button(self.root,text="Editar Memória",font=self.medium_font,command=self.edit_memory)
        self.edit_memory_button.grid(row=2,column=2,pady=10, padx=10)

        self.edit_instructions_button = tk.Button(self.root,text="Editar Instruções",font=self.medium_font,command=self.edit_instructions)
        self.edit_instructions_button.grid(row=3,column=0,pady=10, padx=10)

        self.edit_cache_button = tk.Button(self.root,text="Editar Cache",font=self.medium_font,command=self.edit_cache)
        self.edit_cache_button.grid(row=2,column=1,pady=10, padx=10)

        self.edit_registers_button = tk.Button(self.root,text="Editar Registradores",font=self.medium_font,command=self.edit_registers)
        self.edit_registers_button.grid(row=2,column=0,pady=10, padx=10)

        self.performance_button = tk.Button(self.root,text="Gráfico de Desempenho",font=self.medium_font,command=self.show_performance)
        self.performance_button.grid(row=3,column=2,pady=10, padx=10)

        # Label Instrução Atual / Histórico
        self.current_instruction_label = tk.Label(
            self.root,
            text="Instrução Atual:",
            font=self.large_font,
            wraplength=400,
            justify="left",
            bg="lightyellow",
            anchor="nw",
            relief="solid",
            bd=2
        )
        self.current_instruction_label.place(x=1450,y=50)

        self.history_title_label = tk.Label(
            self.root,
            text="Histórico de Instruções:",
            font=self.large_font,
            wraplength=400,
            justify="left",
            bg="lightyellow",
            anchor="nw",
            relief="solid",
            bd=2
        )
        self.history_title_label.place(x=1450,y=200)

        self.dynamic_history_labels = []
        self.execution_times        = []

        # Inicializa CPU e Carrega Instruções
        backend.initCPU()
        backend.loadDefaultInstructions()
        self.updateAll()

    def updateAll(self):
        self.update_registers()
        self.update_memory()
        self.update_cache_labels()
        self.update_cache_status_label()
        self.update_total_cost_label()

    def update_mapping_mode(self, selected_mode_str):
        if selected_mode_str == "Direto":
            backend.setCacheMappingMode(0)
        else:
            backend.setCacheMappingMode(1)
        self.updateAll()
    def show_component_info(self, comp, info):
        """Mostra uma janela com informações sobre um componente."""
        w = tk.Toplevel(self.root)
        w.title(f"Informação: {comp}")
        tk.Label(
            w, text=info, font=self.medium_font, wraplength=400, justify="left"
        ).pack(padx=10, pady=10)


    def toggle_explanation(self):
        self.explanation_mode = not self.explanation_mode
        backend.setExplanationMode(int(self.explanation_mode))
        st = "Ativado" if self.explanation_mode else "Desativado"
        self.explanation_button.config(text=f"Modo Explicação: {st}")

    def reset(self):
        backend.resetCPU()
        self.canvas.delete("data_path_temp")
        self.canvas.delete("data_path")
        self.updateAll()
        self.current_instruction_label.config(text="Instrução Atual:")
        self.canvas.itemconfig("control_text", text="Unidade de Controle")
        backend.clearHistory()
        for lbl in self.dynamic_history_labels:
            lbl.destroy()
        self.dynamic_history_labels.clear()
        self.execution_times.clear()

    def next_instruction(self):
        backend.nextInstruction()
        self.updateAll()

        op_text = backend.getLastOperationText().decode("utf-8")
        self.canvas.itemconfig("control_text", text=op_text)

        cost = backend.getLastInstructionCost()
        if cost > 0:
            splitted = op_text.split(":")
            if splitted:
                opcode = splitted[0].strip()
            else:
                opcode = "Instr"
            self.execution_times.append((cost, opcode))

        if self.explanation_mode:
            exp = backend.getLastExplanationText().decode("utf-8")
            if exp:
                self.current_instruction_label.config(text=f"Instrução Atual:\n{exp}")
                self.add_to_dynamic_history(exp)
            else:
                self.current_instruction_label.config(text="Instrução Atual:")

        self.parse_and_draw_data_path(op_text)

    def parse_and_draw_data_path(self, operation_text):
        self.canvas.delete("data_path")

        op = operation_text.strip()
        if not op:
            return

        exp_text = backend.getLastExplanationText().decode("utf-8")
        isHit = ("(HIT)" in exp_text) or ("HIT" in exp_text.upper())

        if op.startswith("LOAD:"):
            import re
            matchMem = re.search(r"Memória\[(\d+)\]", op)
            matchReg = re.search(r"->\s*(R[1-4])", op)
            addr = 0
            if matchMem:
                addr = int(matchMem.group(1))
            reg = "R1"
            if matchReg:
                reg = matchReg.group(1)

            if isHit:
                cCoord = self.get_coords_for("cache_box")
                rCoord = self.get_coords_for(reg)
                self.draw_data_path(cCoord, rCoord)
            else:
                mCoord = self.get_coords_for_memory(addr)
                cCoord = self.get_coords_for("cache_box")
                rCoord = self.get_coords_for(reg)
                self.draw_data_path(mCoord, cCoord)
                self.draw_data_path(cCoord, rCoord)

        elif op.startswith("STORE:"):
            import re
            matchReg = re.search(r"STORE:\s*(R[1-4])", op)
            matchMem = re.search(r"Memória\[(\d+)\]", op)
            reg = "R1"
            if matchReg:
                reg = matchReg.group(1)
            addr = 0
            if matchMem:
                addr = int(matchMem.group(1))

            if isHit:
                rCoord = self.get_coords_for(reg)
                cCoord = self.get_coords_for("cache_box")
                self.draw_data_path(rCoord, cCoord)
            else:
                rCoord = self.get_coords_for(reg)
                cCoord = self.get_coords_for("cache_box")
                mCoord = self.get_coords_for_memory(addr)
                self.draw_data_path(rCoord, cCoord)
                self.draw_data_path(cCoord, mCoord)

        elif op.startswith("ADD:") or op.startswith("SUB:"):
            splitted = op.split(":")
            if len(splitted) > 1:
                line = splitted[1].strip()
            else:
                line = op
            if "->" not in line:
                return
            left_part, right_part = line.split("->")
            left_part  = left_part.strip()
            right_part = right_part.strip()

            if "+" in left_part:
                regs = left_part.split("+")
            else:
                regs = left_part.split("-")
            regs = [r.strip() for r in regs]

            aluC = self.get_coords_for("alu_box")
            for s in regs:
                sC = self.get_coords_for(s)
                if sC and aluC:
                    self.draw_data_path(sC, aluC)

            dC = self.get_coords_for(right_part)
            if aluC and dC:
                self.draw_data_path(aluC, dC)

    def get_coords_for(self, name):
        if name in self.register_boxes:
            box_id, _ = self.register_boxes[name]
            x1,y1,x2,y2 = self.canvas.coords(box_id)
            return ((x1+x2)//2, (y1+y2)//2)
        if name=="cache_box":
            x1,y1,x2,y2 = self.canvas.coords(self.cache_box)
            return ((x1+x2)//2,(y1+y2)//2)
        if name=="alu_box":
            x1,y1,x2,y2 = self.canvas.coords(self.alu_box)
            return ((x1+x2)//2,(y1+y2)//2)
        if name=="memory_box":
            x1,y1,x2,y2 = self.canvas.coords(self.memory_box)
            return ((x1+x2)//2,(y1+y2)//2)
        return None

    def get_coords_for_memory(self, index):
        if 0 <= index < len(self.memory_labels):
            x, y = self.canvas.coords(self.memory_labels[index])[:2]
            return (x, y)
        return self.get_coords_for("memory_box")

    def draw_data_path(self, start, end):
        self.canvas.delete("data_path_temp")
        self.canvas.create_line(
            start[0], start[1],
            end[0], end[1],
            arrow=tk.LAST,
            fill="red",
            width=4,
            tags="data_path_temp",
            arrowshape=(30, 35, 12)
        )
        self.root.update()
        time.sleep(1)

    def add_to_dynamic_history(self, explanation_text):
        label = tk.Label(
            self.root,text=explanation_text,font=self.medium_font,
            wraplength=400,justify="left",bg="lightyellow",
            anchor="nw",relief="solid",bd=2
        )
        y_pos = 250 + len(self.dynamic_history_labels)*50
        label.place(x=1450,y=y_pos)
        self.dynamic_history_labels.append(label)

    def update_registers(self):
        r_str = backend.getRegistersString().decode("utf-8")
        parts = r_str.split(",")
        d = {}
        for p in parts:
            if "=" in p:
                k,v = p.split("=")
                d[k.strip()] = v.strip()
        for reg,(box_id,text_id) in self.register_boxes.items():
            val = d.get(reg,"0")
            self.canvas.itemconfig(text_id, text=f"{reg}: {val}")

    def update_memory(self):
        mem_str = backend.getMemoryString().decode("utf-8")
        parts   = mem_str.split(",")
        for i,part in enumerate(parts):
            if i< len(self.memory_labels):
                self.canvas.itemconfig(self.memory_labels[i], text=part)

    def update_cache_labels(self):
        sz = backend.getCacheSize()
        for i in range(sz):
            line_str = backend.getCacheLineString(i).decode("utf-8")
            self.canvas.itemconfig(self.cache_labels[i], text=line_str)

    def update_cache_status_label(self):
        hits   = ctypes.c_int()
        misses = ctypes.c_int()
        backend.getCacheStatus(ctypes.byref(hits), ctypes.byref(misses))
        self.cache_status_label.config(text=f"Cache Hits: {hits.value} | Misses: {misses.value}")

    def update_total_cost_label(self):
        total = backend.getTotalCycles()
        cost  = backend.getLastInstructionCost()
        self.total_cycles_label.config(text=f"Ciclos de Clock (Total): {total}")
        self.current_cost_label.config(text=f"Custo da Instrução Atual: {cost}")

    def show_history(self):
        w = tk.Toplevel(self.root)
        w.title("Histórico de Instruções")
        w.geometry("600x400")
        txt = tk.Text(w, wrap="word", font=self.medium_font)
        txt.pack(expand=True, fill="both", padx=10, pady=10)
        hist_str = backend.getHistoryString().decode("utf-8")
        txt.insert("end", hist_str)
        txt.config(state="disabled")

    def edit_memory(self):
        w = tk.Toplevel(self.root)
        w.title("Editar Memória")
        w.geometry("400x600")
        size = backend.getMemorySize()
        entries = []

        def save():
            for i,e in enumerate(entries):
                try:
                    val = int(e.get())
                    backend.setMemoryValue(i,val)
                except:
                    pass
            self.update_memory()
            w.destroy()

        for i in range(size):
            tk.Label(w,text=f"Endereço {i}:").grid(row=i,column=0,padx=5,pady=5)
            e = tk.Entry(w)
            e.grid(row=i,column=1,padx=5,pady=5)
            cur = backend.getMemoryValue(i)
            e.insert(0,str(cur))
            entries.append(e)

        tk.Button(w,text="Salvar",command=save).grid(row=size,column=0,columnspan=2,pady=10)

    def edit_instructions(self):
        w = tk.Toplevel(self.root)
        w.title("Editar Instruções")
        w.geometry("600x600")

        count   = backend.getInstructionCount()
        entries = []

        def save():
            new_insts = []
            for e in entries:
                line = e.get().strip()
                if line:
                    new_insts.append(line)
            if new_insts:
                arr_type = ctypes.c_char_p * len(new_insts)
                arr = arr_type(*[s.encode("utf-8") for s in new_insts])
                backend.setInstructions(arr, len(new_insts))
            w.destroy()

        for i in range(count):
            line_str = backend.getInstructionLine(i).decode("utf-8")
            tk.Label(w,text=f"Instrução {i}:").grid(row=i,column=0,padx=5,pady=5)
            e = tk.Entry(w,width=50)
            e.grid(row=i,column=1,padx=5,pady=5)
            e.insert(0,line_str)
            entries.append(e)

        tk.Button(w,text="Salvar",command=save).grid(row=count,column=0,columnspan=2,pady=10)

    def edit_cache(self):
        w = tk.Toplevel(self.root)
        w.title("Editar Cache")
        w.geometry("400x600")
        size = backend.getCacheSize()
        entries = []

        def save():
            for i,e in enumerate(entries):
                try:
                    val = int(e.get())
                    backend.setCacheLineData(i,val)
                except:
                    pass
            self.update_cache_labels()
            w.destroy()

        for i in range(size):
            tk.Label(w,text=f"Linha {i} Data:").grid(row=i,column=0)
            e = tk.Entry(w)
            e.grid(row=i,column=1)
            line_str = backend.getCacheLineString(i).decode("utf-8")
            pos = line_str.find("D=")
            if pos!=-1:
                d_val=line_str[pos+2:].strip()
                e.insert(0,d_val)
            entries.append(e)

        tk.Button(w,text="Salvar",command=save).grid(row=size,column=0,columnspan=2,pady=10)

    def edit_registers(self):
        w = tk.Toplevel(self.root)
        w.title("Editar Registradores")
        w.geometry("400x300")

        r_str = backend.getRegistersString().decode("utf-8")
        parts = r_str.split(",")
        reg_map = {}
        for p in parts:
            if "=" in p:
                k,v = p.split("=")
                reg_map[k.strip()] = v.strip()

        entries = []
        for i,reg in enumerate(self.register_names):
            tk.Label(w,text=reg,font=self.medium_font).grid(row=i,column=0)
            e = tk.Entry(w)
            e.grid(row=i,column=1)
            cur = reg_map.get(reg,"0")
            e.insert(0,cur)
            entries.append((reg,e))

        def save():
            for reg,e in entries:
                try:
                    val = int(e.get())
                    backend.setRegisterValue(reg.encode("utf-8"), val)
                except:
                    pass
            self.update_registers()
            w.destroy()

        tk.Button(w,text="Salvar",command=save).grid(row=len(self.register_names),column=0,columnspan=2,pady=10)

    def show_performance(self):
        if not self.execution_times:
            return

        labels  = []
        efforts = []
        for cost, op in self.execution_times:
            labels.append(op)
            efforts.append(cost)

        plt.figure(figsize=(12, 6))
        plt.bar(range(1, len(efforts)+1), efforts, tick_label=labels, color="blue", alpha=0.7)

        plt.gca().spines["top"].set_visible(False)
        plt.gca().spines["right"].set_visible(False)
        plt.gca().spines["left"].set_visible(True)
        plt.gca().spines["bottom"].set_visible(True)

        plt.xlabel("Instrução", fontsize=14)
        plt.ylabel("Esforço Computacional (Ciclos de Clock)", fontsize=14)
        plt.title("Esforço Computacional por Instrução", fontsize=16, pad=30)
        plt.grid(axis="y", linestyle="--", alpha=0.7)

        for i, value in enumerate(efforts):
            plt.text(i+1, value+0.5, str(value), fontsize=10, ha="center")

        plt.show()

if __name__=="__main__":
    root = tk.Tk()
    app = CPUVisualizer(root)
    root.mainloop()
