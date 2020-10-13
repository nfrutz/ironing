start_gcode_string = ";LAYER:"
setting_string = ";SETTING_3 "
end_gcode_string = ";TIME_ELAPSED:"
skin_string = ";TYPE:SKIN\n"
outer_wall_string = ";TYPE:WALL-OUTER"
ironing_enable_string = "ironing_enabled"
mesh_string = ";MESH:"
fan_string = "M106 S"
ironing_string = ";TYPE:SKIN ;IRONING\n"
size_min_x = ";PRINT.SIZE.MIN.X:"
size_min_y = ";PRINT.SIZE.MIN.Y:"
size_min_z = ";PRINT.SIZE.MIN.Z:"
size_max_x = ";PRINT.SIZE.MAX.X:"
size_max_y = ";PRINT.SIZE.MAX.Y:"
size_max_z = ";PRINT.SIZE.MAX.Z:"


class Part:
    def __init__(self, filename):

        self.filename = filename
        self.root = filename
        self.file_lines = []

        directories = filename.split('/')
        self.filename = directories[-1]

        self.ironing_file = ""
        for dir in directories[:-1]:
            self.ironing_file += dir + "/"

        self.ironing_file += "ironing_" + self.filename
        self.ironing_moves = None
        self.ironing_rotated_moves = None

        self.ironing_flows = []
        self.list_of_layers = []

        self.start_gcode = []
        self.end_gcode = []
        # self.layers_lines = []

        self.ironing_enabled = 0
        self.ironing_flow = 0
        self.ironing_inset = 0
        self.speed_ironing = 0
        self.settings = {}
        self.part_has_ironing = False
        self.ironing_settings = {}
        #self.has_ironing = self.search_for_layers()
        self.layer_lines = []

        self.fan_speed = 0
        self.zoffset = 0
        self.center_of_mass = [0,0]

    def read_file(self):
        with open(self.root, 'r') as file:
            self.file_lines = file.readlines()

    def get_start_gcode_from_file(self):
        for line in self.file_lines:
            if start_gcode_string not in line:
                self.start_gcode.append(line)
            else:
                break

    def get_end_gcode_from_file(self):
        end_gcode_string = ";TIME_ELAPSED:"
        for line in self.file_lines[-1:0:-1]:
            if end_gcode_string not in line:
                self.end_gcode.append(line)
            else:
                self.end_gcode.reverse()
                break

    def get_settings_from_file(self):
        settings_line = ""
        for line in self.file_lines:
            if setting_string in line:
                settings_line += line.replace(setting_string, "").strip("\n")

        settings = settings_line.split("\\n")

        for setting in settings:
            if " = " in setting:
                setting_name, setting_value = setting.strip("\\").split(" = ")
                self.settings[setting_name] = setting_value

    def check_for_ironing(self):
        if ironing_enable_string in self.settings:
            self.part_has_ironing = self.settings[ironing_enable_string] == "True"
            self.ironing_settings = [(key, value) for key, value in self.settings.items() if "ironing" in key]
        else:
            self.part_has_ironing = False

        return self.part_has_ironing

    def get_center_of_mass_from_start_gcode(self):
        xmin = 0
        xmax = 0
        ymin = 0
        ymax = 0

        for line in self.start_gcode:
            if size_min_x in line:
                string_slice = line.strip("/n").split(size_min_x)
                xmin = float(string_slice[1])
            elif size_max_x in line:
                string_slice = line.strip("/n").split(size_max_x)
                xmax = float(string_slice[1])
            elif size_min_y in line:
                string_slice = line.strip("/n").split(size_min_y)
                ymin = float(string_slice[1])
            elif size_max_y in line:
                string_slice = line.strip("/n").split(size_max_y)
                ymax = float(string_slice[1])

        self.center_of_mass = [xmin + (xmax - xmin)/2, ymin + (ymax - ymin)/2]

    def get_part_instructions(self):

        self.get_start_gcode_from_file()
        self.get_center_of_mass_from_start_gcode()
        self.get_end_gcode_from_file()

        last_extrusion = 0

        if self.check_for_ironing():
            start_lines = [(line, index) for index, line in enumerate(self.file_lines) if start_gcode_string in line]
            end_lines = [(line, index) for index, line in enumerate(self.file_lines) if end_gcode_string in line]

            if len(start_lines) == len(end_lines):
                for i in range(len(start_lines)):
                    self.layer_lines.append((start_lines[i][0], start_lines[i][1], end_lines[i][1]))
                    new_layer = Layer(i, self.file_lines[start_lines[i][1]:end_lines[i][1] + 1])

                    if i == 0:
                        last_extrusion = 0
                    elif i == len(start_lines) - 1:
                        ironing_instructions = new_layer.get_ironing_instructions_from_layer()
                        self.ironing_moves = Layer(-1, ironing_instructions)
                        self.ironing_moves.set_ironing_skin_code()

                        rotated_moves = self.ironing_moves.rotate_ironing_instructions(center_of_mass=self.center_of_mass)
                        self.ironing_rotated_moves = Layer(-1, rotated_moves)
                        self.ironing_rotated_moves.set_ironing_skin_code()

                    last_extrusion = new_layer.get_extrusion_length(last_extrusion)

                    self.list_of_layers.append(new_layer)

                self.ironing_moves.get_extrusion_length(last_extrusion)
                self.ironing_rotated_moves.get_extrusion_length(last_extrusion)

                for layer in self.list_of_layers:
                    print("Start: %f  End: %f  Length:%f" % (layer.extrusion_start, layer.extrusion_end, layer.extrusion_length))

                layer = self.ironing_moves
                print("Ironing\nStart: %f  End: %f  Length:%f" % (layer.extrusion_start, layer.extrusion_end, layer.extrusion_length))
            else:
                print("List size mismatch")

        else:
            print("Part has no Iroring")

        self.get_z_height_for_part()
        self.get_fan_speed_for_part()

    def add_ironing_to_part(self, layers_to_iron, direction, disable_flow=None, fan_speed=None, z_offset=None):
        with open(self.ironing_file, 'w') as file:
            file.writelines(self.start_gcode)

            length_increment = 0
            for index, iron in enumerate(layers_to_iron):
                if iron == 1:
                    if direction == "opta":
                        if (len(self.list_of_layers) - index) % 2 == 0:
                            layer_gcode = self.list_of_layers[index].get_gcode_modified(length_increment, self.ironing_moves, disable_flow, fan_speed, z_offset)
                        else:
                            layer_gcode = self.list_of_layers[index].get_gcode_modified(length_increment, self.ironing_rotated_moves, disable_flow, fan_speed, z_offset)
                        length_increment += self.ironing_rotated_moves.extrusion_length
                    elif direction == "optb":
                        if (len(self.list_of_layers) - index) % 2 == 0:
                            layer_gcode = self.list_of_layers[index].get_gcode_modified(length_increment, self.ironing_rotated_moves, disable_flow, fan_speed, z_offset)
                        else:
                            layer_gcode = self.list_of_layers[index].get_gcode_modified(length_increment, self.ironing_moves, disable_flow, fan_speed, z_offset)
                        length_increment += self.ironing_moves.extrusion_length
                else:
                    layer_gcode = self.list_of_layers[index].get_gcode_modified(length_increment)

                file.writelines(layer_gcode)

            new_line = get_new_extrusion_on_gcode_line(self.end_gcode[0], length_increment)
            if new_line:
                file.write(new_line)
                file.writelines(self.end_gcode[1:])
            else:
                file.writelines(self.end_gcode[1:])
            # file.writelines(self.settings)

        return True

    def set_advanced_settings(self, fan_speed, zoffset):
        self.fan_speed = fan_speed
        self.zoffset = zoffset

        for layer in self.list_of_layers:
            layer.get_initial_fan_speed()

    def get_z_height_for_part(self):
        for layer in self.list_of_layers:
            h = layer.get_z_height()
            # print("L%s : %s" % (layer.layer_index, h))

    def get_fan_speed_for_part(self):
        fan_lines = [line for line in self.file_lines if fan_string in line]
        m_code, speed = fan_lines[0].strip("\n").split("S")
        last_fan_speed = float(speed)
        for layer in self.list_of_layers:
            last_fan_speed = layer.get_fan_speed(last_fan_speed)
            # print("L%s : %s" % (layer.layer_index, last_fan_speed))


class Layer:

    def __init__(self, index, gcode_lines):
        self.layer_index = index
        self.gcode_lines = gcode_lines
        self.extrusion_length = 0
        self.extrusion_start = 0
        self.extrusion_end = 0
        self.extrusion_to_add = 0

        self.z_height = 0
        self.fan_speed = 0

        self.ironing_z_height = 0
        self.ironing_fan_speed = 0
        self.ironing_flow = 0

        self.number_of_parts = 1
        self.get_number_of_parts()

    def set_ironing_skin_code(self):
        self.gcode_lines[0] = ironing_string

    def get_extrusion_length(self, starting_extrusion):
        self.extrusion_start = starting_extrusion
        self.extrusion_end = 0
        extrusion_reg = []

        for line in self.gcode_lines:
            if "G1" in line and "E" in line:
                substring = line.strip("\n").split(" ")
                substring.sort()
                extrusion_reg.append(float(substring[0].replace("E", "")))

        self.extrusion_end = max(extrusion_reg)
        self.extrusion_length = self.extrusion_end - self.extrusion_start

        return self.extrusion_end

    def get_number_of_parts(self):
        self.number_of_parts = self.gcode_lines.count(mesh_string)

        if self.number_of_parts == 0:  # old versions
            self.number_of_parts = 1

    def get_fan_speed(self, fan_speed):
        fan_lines = [line for line in self.gcode_lines if fan_string in line]
        if fan_lines:
            aux = fan_lines[-1]
            m_code, s_code = aux.strip("\n").split("S")
            self.fan_speed = float(s_code)
        else:
            self.fan_speed = fan_speed

        return self.fan_speed

    def get_z_height(self):
        z_heights = [line for line in self.gcode_lines if ("G1" in line or "G0" in line) and "Z" in line]
        if z_heights:
            aux = z_heights[0]
            g_code, z_code = aux.strip("\n").split("Z")
            self.z_height = float(z_code)
        else:
            self.z_height = -1

        return self.z_height


    def get_ironing_instructions_from_layer(self):
        if self.number_of_parts == 1:
            skin_in_gcode = [index for index, line in enumerate(self.gcode_lines) if skin_string in line]
            ironing_in_gcode = self.gcode_lines[skin_in_gcode[-1]:-1]
            self.gcode_lines = self.gcode_lines[:skin_in_gcode[-1]] + [self.gcode_lines[-1]]
            return ironing_in_gcode
        else:
            pass

    def rotate_ironing_instructions(self, center_of_mass=None):
        return rotate_gcode_lines(self.gcode_lines, center_of_mass)

    def get_gcode_modified(self, extrusion_length, ironing=None, disable_flow=False, fan_speed=-1, z_offset=0):
        gcode = []
        for line in self.gcode_lines[:-1]:
            if "G1" in line and "E" in line:
                new_line = get_new_extrusion_on_gcode_line(line, extrusion_length)
                if new_line:
                    gcode.append(new_line)
            else:
                gcode.append(line)

        ironing_gcode = []
        if ironing:
            for line in ironing.gcode_lines:
                if "G1" in line and "E" in line:
                    if disable_flow:
                        new_line = get_gcode_line_without_extrusion(line)
                        if new_line != "":
                            ironing_gcode.append(new_line)
                    else:
                        new_line = get_new_extrusion_on_gcode_line(line, self.extrusion_end + extrusion_length - ironing.extrusion_start)
                        if new_line:
                            ironing_gcode.append(new_line)
                else:
                    ironing_gcode.append(line)

            if fan_speed >= 0:
                ironing_gcode.insert(1, "M106 S%s\n" % fan_speed)
                ironing_gcode.insert(len(ironing_gcode), "M106 S%s\n" % self.fan_speed)

            if z_offset != 0:
                ironing_gcode.insert(1, "G0 Z%s\n" % str(self.z_height + z_offset))
                ironing_gcode.insert(len(ironing_gcode), "G0 Z%s\n" % str(self.z_height))

            return gcode + ironing_gcode + list(self.gcode_lines[-1])

        else:
            return gcode + list(self.gcode_lines[-1])


def get_new_extrusion_on_gcode_line(line, extrusion_length):
    aux_line = line.strip("\n").split("E")
    if len(aux_line) == 2:
        if len(aux_line[1].split(" ")) == 1:
            return "%sE%.5f\n" % (aux_line[0], float(aux_line[1]) + extrusion_length)
    else:
        print("Error while incrementing the extrusion length.")
        return None

def get_gcode_line_without_extrusion(line):
    aux_line = line.strip("\n").split(" ")
    new_gcode = ""
    if "E" in line and "F" in line and len(aux_line) <= 3:
        pass
    else:
        for command in aux_line:
            if "E" not in command:
                new_gcode += "%s " % command
        new_gcode += "\n"

    return new_gcode

def rotate_gcode_lines(list_of_gcode, center_of_mass=None):
    ironing_rotated_moves = []
    if not center_of_mass:
        center_of_mass = get_center_of_mass_of_gcode(list_of_gcode)

    for line in list_of_gcode:
        if "G1" in line or "G0" in line:
            point_x = None
            point_y = None

            strip_x = line.split('X')
            if len(strip_x) > 1:
                strip_x_2 = strip_x[-1].split(" ")
                point_x = float(strip_x_2[0])

            strip_y = line.split('Y')
            if len(strip_y) > 1:
                strip_y_2 = strip_y[-1].split(" ")
                point_y = float(strip_y_2[0])

            if point_x and point_y:
                point_x_orig = point_x - center_of_mass[0]
                point_y_orig = point_y - center_of_mass[1]

                new_point_x = - point_x_orig + center_of_mass[0]
                new_point_y = point_y_orig + center_of_mass[1]

                split_line = line.strip("\n").split(" ")
                if len(split_line) == 3:
                    # aux_line = "%s X%f Y%f\n" % (split_line[0], point.x, point_y)
                    aux_line = "%s X%f Y%f\n" % (split_line[0], new_point_x, new_point_y)
                    ironing_rotated_moves.append(aux_line)
                elif len(split_line) == 4:
                    # aux_line = "%s X%f Y%f %s" % (split_line[0], point.x, point_y, split_line[-1])
                    if "F" in line and "E" in line:
                        aux_line = "%s %s X%f Y%f %s\n" % (split_line[0], split_line[1], new_point_x, new_point_y, split_line[-1])
                    elif "E" in line:
                        aux_line = "%s X%f Y%f %s\n" % (split_line[0], new_point_x, new_point_y, split_line[-1])
                    elif "F" in line:
                        aux_line = "%s %s X%f Y%f\n" % (split_line[0], split_line[1], new_point_x, new_point_y)

                    ironing_rotated_moves.append(aux_line)
                elif len(split_line) == 5:
                    print("This happens!!!")
                else:
                    print("Something wrong")

            else:
                ironing_rotated_moves.append(line)
        else:
            ironing_rotated_moves.append(line)

    return ironing_rotated_moves

def get_center_of_mass_of_gcode(list_of_gcode):
    list_of_points = []

    for line in list_of_gcode:
        if "G1" in line or "G0" in line:
            point_x = None
            point_y = None

            strip_x = line.split('X')
            if len(strip_x) > 1:
                strip_x_2 = strip_x[-1].split(" ")
                point_x = float(strip_x_2[0])

            strip_y = line.split('Y')
            if len(strip_y) > 1:
                strip_y_2 = strip_y[-1].split(" ")
                point_y = float(strip_y_2[0])

            if point_x and point_y:
                # point = Point([point_x, point_y])
                point = [point_x, point_y]
                list_of_points.append(point)

    if list_of_points:
        points_x = [x[0] for x in list_of_points]
        points_y = [x[1] for x in list_of_points]
        center_of_mass = [sum(points_x) / len(points_x), sum(points_y) / len(points_y)]
    else:
        center_of_mass = [0, 0]
        print("No points found...")

    return center_of_mass

def get_center_of_mass_from_start_gcode(list_of_gcode):
    pass