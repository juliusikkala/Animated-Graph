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
from gi.repository import Gtk, Gdk

class Graph(Gtk.DrawingArea):
    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.add_events(
            Gdk.EventMask.SCROLL_MASK|
            Gdk.EventMask.BUTTON_PRESS_MASK|
            Gdk.EventMask.BUTTON_RELEASE_MASK|
            Gdk.EventMask.BUTTON_MOTION_MASK
        )

        self.last_update = timer()

        self.time = 0
        self.scale = 50
        self.offset = (0, 0)
        self.axis_width = 2
        self.grid_width = 1
        self.function_width = 1
        self.dragging = None
        self.running = False

    def draw_function(self, ctx):
        pass

    def update(self):
        cur_time = timer()
        self.time += cur_time-self.last_update
        self.last_update = cur_time
        if self.running:
            self.queue_draw()

    def start(self):
        self.running = True
        self.update()

    def stop(self):
        self.running=False

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

        #Grid, don't draw if it is too dense
        if self.scale>self.grid_width*10:
            ctx.set_line_width(self.grid_width)
            ctx.set_source_rgb(0.8,0.8,0.8)
            grid_x = (origo[0]%self.scale)+grid_snap
            grid_y = (origo[1]%self.scale)+grid_snap
            
            while grid_x<w:
                ctx.move_to(grid_x, 0)
                ctx.line_to(grid_x, h)
                grid_x+=self.scale

            while grid_y<h:
                ctx.move_to(0, grid_y)
                ctx.line_to(w, grid_y)
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

        self.draw_function(ctx, w, h, origo)

        #Keep the ball rolling...
        if self.running:
            self.update()

    def do_button_press_event(self, event):
        if event.button==1:
            self.dragging = (event.x, event.y)
        return True

    def do_button_release_event(self, event):
        if event.button==1:
            self.dragging = None
        return True

    def do_motion_notify_event(self, event):
        if self.dragging is not None:
            delta = ((event.x-self.dragging[0])/self.scale,
                     (event.y-self.dragging[1])/self.scale)
            self.offset = (self.offset[0]+delta[0], self.offset[1]+delta[1])
            self.dragging = (event.x, event.y)
        return True

    def do_scroll_event(self, event):
        if event.direction==Gdk.ScrollDirection.UP:
            self.scale*=1.1
        elif event.direction==Gdk.ScrollDirection.DOWN:
            self.scale*=0.9
        return True

class CartesianGraph(Graph):
    def __init__(self):
        Graph.__init__(self)

        self.x, self.t = sympy.symbols("x t")
        self.function = None

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

    def draw_function(self, ctx, w, h, origo):
        if self.function == None:
            return

        ctx.set_line_width(self.function_width)
        ctx.set_source_rgb(0,0,1)
        first = True
        screen_x = 0
        screen_step = 1

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
                #Function was not continuous at this point, don't draw a
                #continuous line.
                first = True

            screen_x+=screen_step
        ctx.stroke()

class PolarGraph(Graph):
    def __init__(self):
        Graph.__init__(self)

        self.x, self.t = sympy.symbols("x t")
        self.function = None
        self.angle_max = math.pi*2
        self.angle_step = self.angle_max/1000

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

    def draw_function(self, ctx, w, h, origo):
        if self.function == None:
            return

        ctx.set_line_width(self.function_width)
        ctx.set_source_rgb(0,0,1)
        first = True
        angle = 0

        while angle<self.angle_max:
            try:
                r = float(self.function(angle, self.time))
                x = r*math.cos(angle)
                y = r*math.sin(angle)
                screen_x = x*self.scale+origo[0]
                screen_y = -y*self.scale+origo[1]
                margin = 256
                screen_x = max(-margin, min(screen_x, w+margin))
                screen_y = max(-margin, min(screen_y, h+margin))

                if first:
                    ctx.move_to(screen_x, screen_y)
                    first = False
                else:
                    ctx.line_to(screen_x, screen_y)
            except:
                #Function was not continuous at this point, don't draw a
                #continuous line.
                first = True
            angle += self.angle_step
        ctx.stroke()

class GraphWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Animated Graph", border_width=6)
        self.set_default_size(640, 480)

        default_function="sin(t+x)"

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.controls= Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.graph_box = Gtk.Box()
        self.graph = CartesianGraph()
        self.graph.set_function(default_function)
        self.graph.start()

        self.graph_box.pack_start(self.graph, True, True, 0)

        self.function_entry = Gtk.Entry()
        self.function_entry.set_text(default_function)
        self.function_entry.set_editable(True)
        self.function_entry.connect("activate", self.on_function_activate)

        self.function_mode = Gtk.ComboBoxText()
        self.function_mode.append("cartesian", "Cartesian")
        self.function_mode.append("polar", "Polar")
        self.function_mode.connect("changed", self.on_mode_changed)
        self.function_mode.set_entry_text_column(1)
        self.function_mode.set_active_id("cartesian")

        self.controls.pack_start(self.function_mode, False, True, 0)
        self.controls.pack_start(self.function_entry, True, True, 0)

        vbox.pack_start(self.graph_box, True, True, 0)
        vbox.pack_start(self.controls, False, True, 0)

        self.add(vbox)

    def on_function_activate(self, widget):
        self.graph.stop()
        self.graph.set_function(widget.get_text())
        self.graph.start()

    def on_mode_changed(self, widget):
        self.graph_box.remove(self.graph)
        if widget.get_active_id()=="cartesian":
            self.graph = CartesianGraph()
            self.graph.set_function(self.function_entry.get_text())
        elif widget.get_active_id()=="polar":
            self.graph = PolarGraph()
            self.graph.set_function(self.function_entry.get_text())
        self.graph.start()
        self.graph.show()
        self.graph_box.pack_start(self.graph, True, True, 0)


win = GraphWindow()
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
