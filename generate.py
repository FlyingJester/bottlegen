#!/usr/bin/python
# Generates a bottle reader from a JSON file.

import json
import datetime
import getopt
import sys

# Language output constants
CLANG = 0
MLANG = 1
JSON  = 2

# Default
lang = CLANG

tab = "    "
nl = "\n"

TYPES = ["int", "float", "string"]

c_preamble = """
#include <stdlib.h>
#include <string.h>

static unsigned bottle_read_string_file(FILE *from, struct BottleString *to){
    const unsigned len = fgetc(from);
    to->len = len;
    to->str = (char*)malloc(len);
    {
        const unsigned nread = fread(to->str, 1, len, from);
        if(nread == len)
            return BOTTLE_OK;
        else
            return BOTTLE_FAIL;
    }
}

static unsigned bottle_read_string_mem(const void *from_v, unsigned from_len,
    const unsigned at, unsigned *const len_to, struct BottleString *to){
    
    unsigned i = at;
    const unsigned char *const from = from_v;
    
    if(from_len <= i + 1)
        return BOTTLE_FAIL;
    else{
        const unsigned len = from[i++];
        if(from_len <= i + len)
            return BOTTLE_FAIL;
        to->len = len;
        to->str = (char*)malloc(len);
        memcpy(to->str, from + i, len);
        len_to[0] = len;
    }
    
    return BOTTLE_OK;
}

static void bottle_write_string_file(FILE *to, const struct BottleString *from){
    fputc(from->len, to);
    fwrite(from->str, 1, from->len, to);
}

static void bottle_write_string_mem(void *to_v, unsigned *at,
    const struct BottleString *from){

    unsigned char *const to = to_v;
    to[*at] = from->len;
    memcpy(to + 1, from->str, from->len);
    at[0] += from->len+1;
}

"""

def capitalize(name):
    i = 1
    l = len(name)
    if l == 0:
        return ""
    
    out = name[0].upper()
    while i < l:
        if name[i] == '_':
            i += 1
            while (i < l) and (name[i] == '_'):
                i+=1
            if i < l:
                out += name[i].upper()
        else:
            out += name[i]
        i += 1
    
    return out

def calcTabs(tabs):
    tabn = ""
    i = 0
    while i < tabs:
        tabn += tab
        i += 1
    return tabn

# Base Writer
class Writer:
    def __init__(self, name):
        self.name = name
        self.enums = []
    
    def getName(self):
        return self.name
    
    def beginEnums(self):
        pass
    
    def endEnums(self):
        pass

    def beginBlocks(self):
        pass
    
    def endBlocks(self):
        pass

    def getVariable(self, variable_name, variable_body):
        output = {"name":str(variable_name), "type":"", "attr":{}}
        if type(variable_body) is str or type(variable_body) is unicode:
            output["type"] = str(variable_body)
        elif type(variable_body) is dict:
            if not "type" in variable_body:
                print variable_body
            output["type"] = variable_body["type"]
            if (output["type"] == "string") and ("len" in variable_body):
                output["attr"]["len"] = variable_body["len"]
        else:
            print type(variable_body)
        
        if not ((output["type"] in TYPES) or (output["type"] in self.enums)):
            print ("Invalid type " + output["type"])
            err = "Type must be"
            for t in TYPES:
                err += " " + t
            print (err + " or an enum")
            quit()
        return output

# JSON Writer, outputs an equivalent JSON file as its input
class JSONWriter(Writer):
    def __init__(self, name):
        Writer.__init__(self, name)
    
    def quote(self, str0, suffix = "", output = None):
        if output == None:
            output = self.output
        output.write('"' + str(str0) + '"' + suffix)
    
    def open(self, name):
        self.output = open(name + ".json", "wb")
        self.output.write('{' + nl + tab + '"name":"' + name + '",')

    def close(self):
        self.output.write('}')
        self.output.close()
    
    def beginEnums(self):
        self.output.write(nl + tab + '"enums":{' + nl)

    def endEnums(self):
        self.output.write(tab + "}," + nl)
    
    def writeEnum(self, enum_name, enumeration):
        self.enums.append(str(enum_name))
        self.output.write(tab + tab)
        if len(self.enums) != 1:
            self.output.write(',')
        self.quote(enum_name, ":[")
        if len(enumeration) > 0:
            self.output.write(nl + tab + tab + tab)
            for e in enumeration[:-1]:
                self.quote(e, ',' + nl)
                self.output.write(tab + tab + tab)
            self.quote(enumeration[-1])
            self.output.write(nl + tab + tab)
        
        self.output.write("]" + nl)
    
    def writeVariable(self, var):
        self.quote(var["name"], ':')
        if len(var["attr"]) == 0:
            self.quote(var["type"])
        else:
            self.output.write('{"type":')
            self.quote(var["type"])
            for key, val in var["attr"]:
                self.output.write(',')
                self.quote(key, ':')
                self.quote(val)
            self.output.write('}')

    def beginBlocks(self):
        self.output.write(tab + '"blocks":{' + nl)
    
    def endBlocks(self):
        self.output.write(tab + "}" + nl)
    
    def writeChildren(self, children, tabs):
        tabn = calcTabs(tabs)
        
        if not (str(children["enum"]) in self.enums):
            print ("Invalid enumeration value: " + str(children["enum"]))
            quit()
        
        self.output.write(tabn)
        self.output.write('"children":{ "enum":')
        self.quote(children["enum"], ',' + nl)
        
        l = len(children)
        i = 0
        
        for key in children:
            i += 1
            if key == "enum":
                continue
            self.writeBlock(str(key), children[key], tabs + 1)
            if i != l:
                self.output.write(',')
            self.output.write(nl)
        self.output.write(tabn + "}")
    
    def writeBlock(self, block_name, block, tabs=2):
        tabn = calcTabs(tabs)
        
        self.output.write(tabn)
        self.quote(block_name, ':{' + nl)
        l = len(block)
        i = 0
        for key in block:
            i += 1
            if key == "children":
                self.writeChildren(block["children"], tabs + 1)

            else:
                var = getVariable(key, block[key])
                self.output.write(tabn + tab)
                self.writeVariable(var)
            if i != l:
                self.output.write(',')
            self.output.write(nl)
        self.output.write(tabn + "}")

# C Writer
class CWriter(Writer):
    def __init__(self, name):
        Writer.__init__(self, name)
    
    def open(self, name):
        self.c = open(name + ".c", "wb")
        self.c.write('#include "' + name + '.h"' + nl)
        self.c.write(c_preamble)
        self.h = open(name + ".h", "wb")
                
        self.h.write("#pragma once" + nl)
        self.h.write("/* AUTOGENERATED, DO NOT EDIT" + nl)
        self.h.write(" * Created by libbottle generate.py, ")
        self.h.write(str(datetime.date.today()))
        self.h.write(nl + " */ " + nl + nl)
        inc_guard = "BOTTLE_" + name.upper() + "_HEAD"
        self.h.write("#ifndef " + inc_guard + nl)
        self.h.write("#define " + inc_guard + nl)
        self.h.write(nl + "#include <stdio.h>" + nl)
        self.h.write(nl + "#ifdef __cplusplus" + nl)
        self.h.write('extern "C" {' + nl)
        self.h.write("#endif" + nl)
        self.h.write(nl)
        self.h.write("#ifndef BOTTLE_ENUMS" + nl)
        self.h.write("#define BOTTLE_ENUMS" + nl)
        self.h.write("#define BOTTLE_OK 0" + nl)
        self.h.write("#define BOTTLE_FAIL 1" + nl)
        self.h.write(nl)
        self.h.write("struct BottleString { char *str; unsigned len; }; ")
        self.h.write(nl)
        self.h.write("#endif" + nl + nl)
    
    def close(self):
        self.h.write(nl + "#ifdef __cplusplus" + nl)
        self.h.write('}' + nl)
        self.h.write("#endif" + nl)
        self.h.write(nl + "#endif" + nl)
        
        self.c.close()
        self.h.close()
    
    def writeMemReaderChildren(self, children, tabs, parents):
        pass

    def writeFileReaderChildren(self, children, tabs, parents):
        enum_name_u = capitalize(children["enum"])
        tabn = calcTabs(tabs)
        self.c.write(tabn + "out->")
        for p in parents:
            self.c.write(p + ".")
        self.c.write(enum_name_u + " = fgetc(from); " + nl)
        self.c.write(tabn + "switch(out->")
        for p in parents:
            self.c.write(p + ".")
        self.c.write(enum_name_u + "){" + nl)
        for key in children:
            if key == "enum":
                continue
            self.c.write(tabn + "if(feof(from) != 0) return BOTTLE_FAIL;" + nl)
            self.c.write(tabn + tab + "case e" + capitalize(key) + ":" + nl)
            self.writeFileReader(key, children[key], tabs + 2, parents + [enum_name_u + "Data", key])
            self.c.write(tabn + tab + "break;" + nl)
        self.c.write(tabn + "}" + nl)

    def writeMemReader(self, block_name, block, tabs = 1, parents = []):
        cap_name = capitalize(block_name)

    def writeFileReader(self, block_name, block, tabs = 1, parents = []):
        cap_name = capitalize(block_name)
        tabn = calcTabs(tabs)
        for key in block:
            if key == "children":
                continue
            self.c.write(tabn + "if(feof(from) != 0) return BOTTLE_FAIL;" + nl)
            var = self.getVariable(key, block[key])
            if var["type"] == "string":
                self.c.write(tabn + "bottle_read_string_file(from, &(out->")
                for p in parents:
                    self.c.write(p + ".")
                self.c.write(var["name"] + "));" + nl)
            elif var["type"] in self.enums:
                self.c.write(tabn + "{ unsigned i; fread(&i, 1, 4, from);" + nl)
                self.c.write(tabn + tab + "out->")
                for p in parents:
                    self.c.write(p + ".")
                self.c.write(var["name"] + " = i; }" + nl)
            else:
                self.c.write(tabn + "fread(&(out->")
                for p in parents:
                    self.c.write(p + ".")
                self.c.write(var["name"] + "), 1, 4, from);" + nl)
        if "children" in block:
            self.c.write(tabn + "{" + nl)
            self.writeFileReaderChildren(block["children"], tabs + 1, parents)
            self.c.write(tabn + "}" + nl)

    def writeMemWriterChildren(self, children, tabs, parents):
        pass

    def writeFileWriterChildren(self, children, tabs, parents):
        enum_name_u = capitalize(children["enum"])
        tabn = calcTabs(tabs)
        self.c.write(tabn + "fputc(from->")
        for p in parents:
            self.c.write(p + ".")
        self.c.write(enum_name_u + ", to); " + nl)
        self.c.write(tabn + "switch(from->")
        for p in parents:
            self.c.write(p + ".")
        self.c.write(enum_name_u + "){" + nl)
        for key in children:
            if key == "enum":
                continue
            self.c.write(tabn + tab + "case e" + capitalize(key) + ":" + nl)
            self.writeFileWriter(key, children[key], tabs + 2, parents + [enum_name_u + "Data", key])
            self.c.write(tabn + tab + "break;" + nl)
        self.c.write(tabn + "}" + nl)

    def writeMemWriter(self, block_name, block, tabs = 1, parents = []):
        cap_name = capitalize(block_name)

    def writeFileWriter(self, block_name, block, tabs = 1, parents = []):
        cap_name = capitalize(block_name)
        tabn = calcTabs(tabs)
        for key in block:
            if key == "children":
                continue
            var = self.getVariable(key, block[key])
            if var["type"] == "string":
                self.c.write(tabn + "bottle_write_string_file(to, &(from->")
                for p in parents:
                    self.c.write(p + ".")
                self.c.write(var["name"] + "));" + nl)
            elif var["type"] in self.enums:
                self.c.write(tabn + "{ const unsigned i = from->")
                for p in parents:
                    self.c.write(p + ".")
                self.c.write(var["name"] + "; fwrite(&i, 1, 4, to); };" + nl)
            else:
                self.c.write(tabn + "fwrite(&(from->")
                for p in parents:
                    self.c.write(p + ".")
                self.c.write(var["name"] + "), 1, 4, to);" + nl)
        if "children" in block:
            self.c.write(tabn + "{" + nl)
            self.writeFileWriterChildren(block["children"], tabs + 1, parents)
            self.c.write(tabn + "}" + nl)
    
    def writeEnum(self, enum_name_l, enumeration):
        l = len(enumeration)
        enum_name = "EnumBottle" + capitalize(enum_name_l)
        self.enums.append(enum_name_l)
        if l == 0:
            self.h.write("typedef unsigned " + enum_name + ";" + nl)
        else:
            self.h.write("enum " + enum_name + "{" + nl)
            for e in enumeration:
                self.h.write(tab + "e" + capitalize(str(e)) +"," + nl)
            self.h.write(tab + "NUM_" + capitalize(enum_name_l) + nl + "};" + nl)
    
    def writeChildren(self, children, tabs):
        tabn0 = calcTabs(tabs - 1)
        tabn = tabn0 + tab
        enum_name_u = capitalize(children["enum"])
        enum_name = "EnumBottle" + enum_name_u
        self.h.write(tabn0 + "enum " + enum_name + " " + enum_name_u + ";" + nl)
        self.h.write(tabn0 + "union{" + nl)

        for key in children:
            if key == "enum":
                continue
            child = children[key]
            if len(child) == 0:
                self.h.write(tabn + "/* No members for " + key + "*/" + nl)
            else:
                self.h.write(tabn + "struct {" + nl)
                self.writeBlock(key, child, tabs + 1, False)
                self.h.write(tabn + "} " + key + ";" + nl)
            
        
        self.h.write(tabn0 + "}" + enum_name_u + "Data;" + nl)

    def writeBlock(self, block_name, block, tabs=1, write_struct = True):
        tabn0 = calcTabs(tabs - 1)
        tabn = tabn0 + tab
        cap_name = capitalize(block_name)
        if write_struct:
            mem_reader = "unsigned Bottle_Load" + cap_name + "Mem(struct Bottle" + cap_name + " *out, const void *mem, unsigned len)"
            file_reader = "unsigned Bottle_Load" + cap_name + "File(struct Bottle" + cap_name + " *out, FILE *from)"
            
            mem_writer = "void *Bottle_Write" + cap_name + "Mem(const struct Bottle" + cap_name + "* from, unsigned *size_out)"
            file_writer = "void Bottle_Write" + cap_name + "File(const struct Bottle" + cap_name + "* from, FILE *to)"
            
            self.h.write(tabn0)
            self.h.write("struct Bottle" + cap_name + ";" + nl)
            self.h.write(nl)
            self.h.write(mem_reader + ";" + nl)
            self.h.write(file_reader + ";" + nl)
            self.h.write(mem_writer + ";" + nl)
            self.h.write(file_writer + ";" + nl)

            self.c.write(mem_writer  +"{" + nl)
            self.writeMemWriter(block_name, block)
            self.c.write("}" + nl)

            self.c.write(file_writer  +"{" + nl)
            self.writeFileWriter(block_name, block)
            self.c.write("}" + nl)

            self.c.write(mem_reader  +"{" + nl)
            self.writeMemReader(block_name, block)
            self.c.write(tab + "return BOTTLE_OK;" + nl + "}" + nl)

            self.c.write(file_reader  +"{" + nl)
            self.writeFileReader(block_name, block)
            self.c.write(tab + "return BOTTLE_OK;" + nl + "}" + nl)

            self.h.write("struct Bottle" + cap_name + " { " + nl)

        for key in block:
            if key == "children":
                continue
            var = self.getVariable(key, block[key])
            self.h.write(tabn)
            if var["type"] == "string":
                self.h.write("struct BottleString ")
            if var["type"] in self.enums:
                self.h.write("enum EnumBottle" + capitalize(var["type"]) + ' ')
            else:
                self.h.write(var["type"] + ' ')
            self.h.write(var["name"] + ";" + nl)
        
        if "children" in block:
            self.writeChildren(block["children"], tabs+1)
        if write_struct:
            self.h.write(calcTabs(tabs - 1) + "};" + nl)

# Mercury Writer
class MWriter(Writer):

    def __init__(self, name):
        Writer.__init__(self, name)
    
    def open(self, name):
        self.src_name = name
        self.file = open(self.src_name + ".m", "wb")
        self.int = ""
        self.imp = ""
        self.small_types = ""
        self.foreign_exports = []
        self.converts = []
        self.enum_defs = {}
        self.written_types = []

    def close(self):
        if len(self.int)==0 and len(self.imp)==0 and len(self.small_types)==0:
            return
        
        out = self.file
        out.write(":- module " + self.src_name + "." + nl)
        out.write("% AUTOGENERATED, DO NOT EDIT" + nl)
        out.write("% Created by libbottle generate.py, ")
        out.write(str(datetime.date.today()))
        out.write(nl)
        out.write(":- interface." + nl + nl)
        out.write(":- import_module buffer." + nl + nl)
        out.write(":- use_module io." + nl + nl)
        out.write(self.small_types)
        out.write(nl)
        out.write(self.int)
        out.write(nl)
        for convert in self.converts:
            name = convert["name"] + "_" + convert["child"]
            out.write(":- pred " + name)
            out.write("(" + convert["name"] + "_data, " + convert["child"] + ").")
            out.write(nl)
            out.write(":- mode " + name)
            out.write("(in, out) is semidet.")
            out.write(nl)
            out.write(":- mode " + name)
            out.write("(out, in) is det.")
            out.write(nl)
            out.write(nl)
        out.write(nl)
        out.write(":- implementation." + nl + nl)
        out.write(":- import_module int." + nl)
        out.write(":- use_module string." + nl)
        out.write(":- use_module list." + nl)
        out.write(":- use_module char." + nl)
        out.write("""

:- pred write_string(string::in, int::in, int::in, io.io::di, io.io::uo) is det.
write_string(Str, I, N, !IO) :-
    ( I = N ->
        true
    ;
        string.det_index(Str, I, Ch),
        char.to_int(Ch, CodePoint),
        io.write_byte(CodePoint, !IO),
        write_string(Str, I + 1, N, !IO)
    ).
""")
        out.write(":- pred float_to_bytes(float::in, int::out, int::out, int::out, int::out) is det." + nl)
        out.write(":- pred bytes_to_float(float::out, int::in, int::in, int::in, int::in) is det." + nl)
        out.write(":- pred int_to_bytes(int::in, int::out, int::out, int::out, int::out) is det." + nl)
        out.write(":- pred bytes_to_int(int::out, int::in, int::in, int::in, int::in) is det." + nl)
        out.write(':- pragma foreign_proc("C", float_to_bytes(In::in, O0::out, O1::out, O2::out, O3::out),' + nl)
        out.write(tab + "[promise_pure, thread_safe, does_not_affect_liveness, will_not_call_mercury, will_not_throw_exception]," + nl)
        out.write(tab + '"const float f=In;const unsigned char *const uc=(unsigned char*)&f;'+nl+tab)
        i = 0
        while i < 4:
            si = str(i)
            out.write("O" + si + "=uc[" + si + "];")
            i += 1
        out.write(tab + '").' + nl)

        out.write(':- pragma foreign_proc("C", bytes_to_float(Out::out, I0::in, I1::in, I2::in, I3::in),' + nl)
        out.write(tab + "[promise_pure, thread_safe, does_not_affect_liveness, will_not_call_mercury, will_not_throw_exception]," + nl)
        out.write(tab + '"float f;unsigned char *const uc=(unsigned char*)&f;'+nl+tab)
        i = 0
        while i < 4:
            si = str(i)
            out.write("uc[" + si + "]=I" + si + ";")
            i += 1
        out.write(tab + "Out = f;" + nl)
        out.write(tab + '").' + nl)
        
        out.write(':- pragma foreign_proc("C", int_to_bytes(In::in, O0::out, O1::out, O2::out, O3::out),' + nl)
        out.write(tab + "[promise_pure, thread_safe, does_not_affect_liveness, will_not_call_mercury, will_not_throw_exception]," + nl)
        out.write(tab + '"const int i=In;const unsigned char *const uc=(unsigned char*)&i;'+nl+tab)
        i = 0
        while i < 4:
            si = str(i)
            out.write("O" + si + "=uc[" + si + "];")
            i += 1
        out.write(tab + '").' + nl)

        out.write(':- pragma foreign_proc("C", bytes_to_int(Out::out, I0::in, I1::in, I2::in, I3::in),' + nl)
        out.write(tab + "[promise_pure, thread_safe, does_not_affect_liveness, will_not_call_mercury, will_not_throw_exception]," + nl)
        out.write(tab + '"int i;unsigned char *const uc=(unsigned char*)&i;'+nl+tab)
        i = 0
        while i < 4:
            si = str(i)
            out.write("uc[" + si + "]=I" + si + ";")
            i += 1
        out.write(tab + "Out = i;" + nl)
        out.write(tab + '").' + nl + nl)
        
        for foreign_export in self.foreign_exports:
            out.write(foreign_export)
            out.write(nl)
        
        for convert in self.converts:
            name = convert["name"]
            child = convert["child"]
            out.write(name + "_type(" + child + "(_)) = " + child + "." + nl)
            predname = name + "_" + child
            out.write(predname + "(" + child + "(That), That)." + nl)
            out.write(':- pragma foreign_export("C", ')
            out.write(predname + '(in, out), ')
            out.write('"' + capitalize(self.src_name) + '_Get' + capitalize(predname) + '").' + nl)
            out.write(':- pragma foreign_export("C", ')
            out.write(predname + '(out, in), ')
            out.write('"' + capitalize(self.src_name) + '_Create' + capitalize(predname) + '").' + nl)
            out.write(nl)
        out.write(nl)
        
        out.write(self.imp)
        out.write(nl)

        self.small_types = ""
        self.int = ""
        self.imp = ""
    
    def writeEnum(self, enum_name, enumeration):
        self.enums.append(enum_name)
        self.enum_defs.update({enum_name:enumeration})
        self.written_enums = []
    
    def writeArityZeroEnum(self, enum_name, enumeration):
        self.small_types += ":- type " + enum_name + " ---> "
        l = len(enumeration)
        if l == 0:
            self.small_types += enum_name + "_unit." + nl + nl
        elif l == 1:
            self.small_types += enumeration[0] + "." + nl + nl
        else:
            self.small_types += nl
            foreign_export = ':- pragma foreign_decl("C",'+nl
            foreign_enum = ':- pragma foreign_enum("C",'+enum_name+'/0,['+nl
            foreign_export += tab + '"enum Enum' + capitalize(enum_name) + "Type{" + nl
            for e in enumeration[:-1]:
                self.small_types += tab + e + " ;" + nl
                foreign_export += tab + "e" + capitalize(e) + "," + nl
                foreign_enum += tab + e + ' - "e' + capitalize(e) + '",' + nl
            self.small_types += tab + enumeration[-1] + "." + nl + nl
            e = capitalize(enumeration[-1])
            foreign_export += tab + "e" + e + nl + '};").' + nl
            foreign_enum += tab + enumeration[-1] + ' - "e' + e + '"]).' + nl
            self.foreign_exports += [foreign_export, foreign_enum]

    def writeEnumType(self, enum_name):
        if enum_name in self.written_enums:
            return
        self.written_enums.append(enum_name)
        enumeration = self.enum_defs[enum_name]
        self.writeArityZeroEnum(enum_name, enumeration)
        
    def writeType(self, name, block):
        if name in self.written_types:
            return
        self.written_types.append(name)
        
        if "children" in block:
            for child in block["children"]:
                if child != "enum":
                    self.small_types += ":- type " + child + "." + nl
            self.small_types += ":- type " + name + "_data --->"
            first = True
            children_names = []
            self.int += ":- func " + name + "_type(" + name + "_data) = " + name + "_type." + nl
            self.foreign_exports.append(
                ':- pragma foreign_export("C", ' + name + '_type(in) = (out), "' + capitalize(self.src_name)+'_Get'+capitalize(name) + 'Type").' + nl)
            for child in block["children"]:
                if child == "enum":
                    continue
                if not first:
                    self.small_types += " ;"
                first = False
                self.small_types += nl
                self.small_types += tab + child + "(" + child + ")"
                self.converts.append({"name":name, "child":child})
                children_names.append(child)
            self.small_types += "." + nl
            self.writeArityZeroEnum(name + "_type", children_names)
        
        if len(block) == 0:
            self.small_types += ":- type " + name + " ---> " + name + "." + nl + nl
        else:
            self.small_types += ":- type " + name + " ---> " + name + "("
            self.int += ":- pred examine_" + name + "("
            args = ""
            sig = ""
            n = 0
            first = True
            for key in block:
                if key == "enum":
                    continue
                if not first:
                    sig += ", "
                    args += ", "
                first = False
                if key == "children":
                    sig += name + "_data"
                    args += capitalize(name)+"Data" + str(n)
                else:
                    var = self.getVariable(key, block[key])
                    sig += var["type"]
                    args += capitalize(var["type"]) + str(n)
                n += 1
            self.small_types += sig + ")." + nl + nl
            self.int += sig + ", " + name + ")." + nl
            examine_body = "examine_" + name + "("
            examine_body += args +", " + name + "(" + args + "))." + nl
            foreign_export_create =  ':- pragma foreign_export("C", examine_' + name + '('
            foreign_export_get = foreign_export_create
            imode = ""
            omode = ""
            while n > 1:
                n -= 1
                imode += "in,"
                omode += "out,"
            imode += "in,out"
            omode += "out,in"
            self.int += ":- mode examine_" + name + "(" + imode + ") is det." + nl
            self.int += ":- mode examine_" + name + "(" + omode + ") is det." + nl
            foreign_export_create += imode +'), "' + capitalize(self.src_name) + "_Create" + capitalize(name) + '").' + nl
            foreign_export_get += omode +'), "' + capitalize(self.src_name) + "_Get" + capitalize(name) + '").' + nl
            self.foreign_exports += [examine_body, foreign_export_create, foreign_export_get]            
    
    def writeBlock(self, block_name, block):
        # self.writeType(block_name, block)
        self.writeType(block_name, block)
        read_pred = "read_" + block_name
        write_pred = "write_" + block_name

        self.int += ":- pred " + write_pred + "(" + block_name + "::in, io.io::di, io.io::uo) is det." + nl + nl
        self.int += "% " + read_pred + "(Buffer, !ByteIndex, Result)." + nl
        if len(block) == 0:
            self.int += ":- pred " + read_pred + "(buffer::in, int::in, int::out, " + block_name + "::out) is det." + nl + nl
            self.imp += read_pred + "(_, !I, " + block_name + ")." + nl + nl
            self.imp += write_pred + "(_, !IO)." + nl + nl
            return

        # Write reader
        self.int += ":- pred " + read_pred + "(buffer::in, int::in, int::out, " + block_name + "::out) is semidet." + nl + nl

        self.imp += read_pred + "(Buffer, I0, IOut, Out) :- " + nl
        # Get all the values...
        i = 1
        istr = "I0"
        istrnext = "I1"
        size = 0
        for key in block:
            if key == "children":
                self.imp += tab + "get_8(Buffer, " + istr + ", Byte" + istr + ")," + nl
                self.imp += tab + "(" + nl
                first = True
                n = 0
                for child in block["children"]:
                    if child == "enum":
                        continue

                    self.writeType(child, block["children"][child])
                    if not first:
                        self.imp += tab + ";" + nl
                    first = False
                    self.imp += tab + tab + "Byte" + istr + " = " + str(n) + "," + nl
                    self.imp += tab + tab + "read_" + child + "(Buffer, " + istr + "+1, " + istrnext + ", Child_" + child + ")," + nl
                    self.imp += tab + tab + "Child = " + child + "(Child_" + child + ")" + nl
                    n += 1
                self.imp += tab + ")," + nl

                istr = istrnext
                istrnext = "I" + str(i)
                i += 1
            else:
                var = self.getVariable(key, block[key])
                t = var["type"]
                if t == "string":
                    self.imp += tab + "get_8(Buffer, " + istr + ", TextSize" + istr + ")," + nl
                    self.imp += tab + "get_ascii_string(Buffer, " + istr + "+1, TextSize" + istr + ", " + capitalize(key) + ")," + nl
                    self.imp += tab + istrnext + " - 1 = TextSize" + istr + " + " + istr + "," + nl
                    i += 1
                    istr = istrnext
                    istrnext = "I" + str(i)
                elif t in self.enums:
                    self.writeEnumType(t)
                    self.imp += tab + "get_byte_32(Buffer, " + istr + ", Int" + istr + ")," + nl
                    self.imp += tab + "(" + nl
                    n = 0
                    for e in self.enum_defs[t]:
                        if n != 0:
                            self.imp += tab + ";" + nl
                        self.imp += tab + tab + "Int" + istr + " = " + str(n) + "," + nl
                        self.imp += tab + tab + capitalize(key) + " = " + e + nl
                        n += 1
                    self.imp += tab + ")," + nl
                else:
                    self.imp += tab + "get_byte_32(Buffer, "+istr+", "+capitalize(key) + ")," + nl
                    self.imp += tab + istrnext + " - 4 = " + istr + "," + nl
                    i += 1
                    istr = istrnext
                    istrnext = "I" + str(i)
        self.imp += tab + "IOut = " + istr + "," + nl

        self.imp += tab + "Out = " + block_name + "("

        first = True
        guts = ""
        for key in block:
            if not first:
                guts += ", "
            first = False
            if key == "children":
                guts += "Child"
            else:
                guts += capitalize(key)
        self.imp += guts + ")." + nl + nl

        # Write writer
        self.imp += write_pred + "(" + block_name + "(" + guts + "), !IO) :-" + nl
        for key in block:
            if key == "children":
                self.imp += tab + "(" + nl
                n = 0
                for child in block["children"]:
                    if child == "enum":
                        continue
                    if n != 0:
                        self.imp += tab + ";" + nl
                    self.imp += tab + tab + "Child = " + child + "(Child" + capitalize(child) + "), io.write_byte(" + str(n) + ", !IO)," + nl
                    self.imp += tab + tab + "write_" + child + "(Child" + capitalize(child) + ", !IO)" + nl
                    n += 1
                self.imp += tab + ")," + nl
            else:
                ckey = capitalize(key)
                var = self.getVariable(key, block[key])
                t = var["type"]
                if t == "string":
                    self.imp += tab + "string.length(" + ckey + ") = 0+Len" + ckey + "," + nl
                    self.imp += tab + "io.write_byte(Len" + ckey + ", !IO)," + nl
                    self.imp += tab + "write_string(" + ckey + ", 0, Len" + ckey + ", !IO)," + nl
                elif t == "float" or t == "int":
                    if t == "float":
                        self.imp += tab + "float_to_bytes(" + ckey
                    elif t == "int":
                        self.imp += tab + "int_to_bytes(" + ckey
                    else:
                        print ("INTERNAL ERROR: Invalid type " + t)
                        quit()
                    i = 0
                    while i < 4:
                        self.imp += ","+ckey+str(i)
                        i += 1
                    self.imp += ")," + nl
                    i = 0
                    while i < 4:
                        self.imp += tab + "io.write_byte(" + ckey + str(i) + ", !IO)," + nl
                        i += 1
                    pass
                elif t in self.enums:
                    self.imp += tab + "(" + nl
                    n = 0
                    for e in self.enum_defs[t]:
                        if n != 0:
                            self.imp += tab + ";" + nl
                        self.imp += tab + tab + ckey + " = " + e + ", io.write_byte(" + str(n) + ", !IO)" + nl
                        n += 1
                    self.imp += tab + ")," + nl
                else:
                    print ("INTERNAL ERROR: Invalid type " + t)
                    quit()
        self.imp += tab + "true." + nl + nl

        if "children" in block:
            for child in block["children"]:
                if child == "enum":
                    continue
                self.writeBlock(child, block["children"][child])

# Generation functions and main

def help():
    if len(sys.argv) == 0:
        name = "generate.py"
    else:
        name = sys.argv[0]
    print ("USAGE: " + name + " [OPTIONS] INPUT")
    print ("OPTIONS:")
    print ("    --help, -h")
    print ("        Displays this help message and exits")
    print ("    --lang LANG, -lLANG")
    print ("        Sets the output language. Choices are c, m[ercury], or j[son]")
    print ("    --nl {DOS|UNIX}, -n{d|u}")
    print ("        Sets line endings to dos or unix. Default is unix.")
    print ("    --tabs N, -t[n]")
    print ("        Use N spaces for tabs, or if zero (or just -t) use tab characters")

def iop(i, p):
    return (i == "-" + p[0]) or (i == "--" + p) or (i == p[0]) or (i == p)

if len(sys.argv) < 2:
    help()
    quit()
else:
    opts, args = getopt.getopt(sys.argv[1:], 'ht:l:n:', ["lang=", "nl=", "tabs=", "help"])
    for opt, x in opts:
        if iop(opt, "help"):
            help()
            quit()
    
    if len(args) == 0:
        print ("No input files specified")
    
    for opt, val in opts:
        l = val.lower()
        if iop(opt, "lang"):
            if iop(l, "c++") or l == "c":
                lang = CLANG
            elif iop(l, "mercury"):
                lang = MLANG
            elif iop(l, "json"):
                lang = JSON
            else:
                print ("Invalid language: " + l)
                quit()
        if iop(opt, "nl"):
            if iop(l, "dos") or iop(l, "windows") or iop(l, "msdos") or l == "ms-dos":
                nl = "\r\n"
            elif iop(l, "unix") or iop(l, "linux") or l == "n":
                nl = "\n"
            else:
                print ("Invalid line ending: " + l)
                quit()
        if iop(opt, "tabs"):
            if val == "":
                tab = "\n"
            else:
                try:
                    n = int(val)
                    if n == 0:
                        tab = "\n"
                    else:
                        tab = ""
                        i = 0
                        while i < n:
                            tab += ""
                except:
                    print ("Invalid tabs: " + val)
                    quit()

    if len(args) == 0:
        quit()

    # Do actual parsing
    for input in args:
        infile = open(input, "rb")
        input_object = json.loads(infile.read())
        if not ("name" in input_object):
            print ("Input has no name property")
            quit()
        else:
            name = input_object["name"]
        if lang == CLANG:
            writer = CWriter(name)
        elif lang == MLANG:
            writer = MWriter(name)
        elif lang == JSON:
            writer = JSONWriter(name)
        else:
            print ("INTERNAL ERROR: Invalid language " + str(lang))
            quit()
        
        writer.open(str(name))
        
        # Write all enums
        if "enums" in input_object:
            enums = input_object["enums"]
            writer.beginEnums()
            for e in enums:
                writer.writeEnum(e, enums[str(e)])
            writer.endEnums()
        
        # Write blocks
        if "blocks" in input_object:
            writer.beginBlocks()
            blocks = input_object["blocks"]
            for b in blocks:
                writer.writeBlock(b, blocks[str(b)])
            writer.endBlocks()
        
        writer.close()
        
