#!/usr/bin/env python3
#The MIT License (MIT)
#
#Copyright (c) 2016 Julius Ikkala
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
import sympy
import gi
import cairo
import math
from timeit import default_timer as timer

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class Graph(Gtk.DrawingArea):
    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.last_update = timer()

        self.x, self.t = sympy.symbols("x t")

        self.function = None
        self.time = 0
        self.scale = 50
        self.step = 1/self.scale
        self.offset = (0, 0)
        self.axis_width = 2
        self.grid_width = 1
        self.function_width = 1

        self.update()

    def set_function(self, function_str):
        try:
            function_expr = sympy.sympify(function_str)
            if not {self.x, self.t}.issuperset(function_expr.free_symbols):
                print("Unknown symbols in function "+function_str)
                self.function = None
            else:
                self.function = sympy.lambdify((self.x, self.t), function_expr)
        except:
            self.function = None

        self.time = 0

    def update(self):
        cur_time = timer()
        self.time += cur_time-self.last_update
        self.last_update = cur_time
        self.queue_draw()

    def do_draw(self, ctx):
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        #Clear with white
        ctx.set_source_rgb(1,1,1)
        ctx.rectangle(0,0,w,h)
        ctx.fill()

        #Render grid and axes
        axis_snap=(self.axis_width/2)%1
        grid_snap=(self.grid_width/2)%1
        origo = (round(w*0.5+self.offset[0]*self.scale),
                 round(h*0.5+self.offset[1]*self.scale))

        #Grid
        ctx.set_line_width(self.grid_width)
        ctx.set_source_rgb(0.8,0.8,0.8)
        grid_x = 0
        grid_y = 0
        while grid_x<w/2:
            ctx.move_to(origo[0]+grid_x+grid_snap, 0)
            ctx.line_to(origo[0]+grid_x+grid_snap, h)

            ctx.move_to(origo[0]-grid_x+grid_snap, 0)
            ctx.line_to(origo[0]-grid_x+grid_snap, h)
            grid_x+=self.scale

        while grid_y<h/2:
            ctx.move_to(0, origo[1]+grid_y+grid_snap)
            ctx.line_to(w, origo[1]+grid_y+grid_snap)

            ctx.move_to(0, origo[1]-grid_y+grid_snap)
            ctx.line_to(w, origo[1]-grid_y+grid_snap)
            grid_y+=self.scale

        ctx.stroke()

        #Axes
        ctx.set_line_width(self.axis_width)
        ctx.set_source_rgb(0,0,0)
        ctx.move_to(origo[0]+axis_snap, 0)
        ctx.line_to(origo[0]+axis_snap, h)
        ctx.move_to(0, origo[1]+axis_snap)
        ctx.line_to(w, origo[1]+axis_snap)
        ctx.stroke()

        #Render function with given step
        ctx.set_line_width(self.function_width)
        ctx.set_source_rgb(0,0,1)
        if self.function != None:
            first = True
            screen_x = 0
            screen_step = self.step*self.scale

            while screen_x<w:
                x = (screen_x-origo[0])/self.scale
                try:
                    y = self.function(x, self.time)
                    screen_y = -float(y)*self.scale+origo[1]
                    margin = 256
                    screen_y = max(-margin, min(screen_y, h+margin))

                    if first:
                        ctx.move_to(screen_x, screen_y)
                        first = False
                    else:
                        ctx.line_to(screen_x, screen_y)
                except:
                    pass
                screen_x+=screen_step

        ctx.stroke()

        #Keep the ball rolling...
        self.update()

class GraphWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Animated Graph", border_width=6)
        self.set_default_size(640, 480)

        default_function="sin(t+x)"

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.graph = Graph()
        self.graph.set_function(default_function)

        self.function_entry = Gtk.Entry()
        self.function_entry.set_text(default_function)
        self.function_entry.set_editable(True)
        self.function_entry.connect("activate", self.on_function_activate)

        vbox.pack_start(self.graph, True, True, 0)
        vbox.pack_start(self.function_entry, False, True, 0)

        self.add(vbox)

    def on_function_activate(self, widget):
        self.graph.set_function(widget.get_text())

win = GraphWindow()
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
