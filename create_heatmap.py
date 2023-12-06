import csv
import cv2
import math
import numpy as np
import os
import sys

# canvas size multiplier
# 1.0 will give images of 1100 x 1100 (used for publication)
SIZE_MULTIPLIER = 1.0

# constants
RIGHT_EYE = 0
LEFT_EYE = 1
BOTH_EYES = 2
SIDE_LABELS = { RIGHT_EYE: "right",\
                LEFT_EYE: "left",\
                BOTH_EYES: "both" }

ADD_LABELS = False
PREVIEW = False
BIG_STACK_IMAGE = False

# if true, will normalise data to 0-255 for heatmap generation
SCALE_LESION_COUNTS = False

# set to True to create a CSV file after every image processed. Useful for
# creating animations and stuff.
SAVE_INTERMEDIATE_DATA = False
INTERMEDIATE_DIR = "int_data"
if SAVE_INTERMEDIATE_DATA and not os.path.exists(INTERMEDIATE_DIR):
    os.makedirs(INTERMEDIATE_DIR)

# distance (in pixels) from the optic nerve to the macular in each scaled image
NERVE_MAC_DIST = int(250 * SIZE_MULTIPLIER)

# Vertical distance (in pixels) from the optic nerve to the macular in each
# scaled image. Used to rotate each image to the same orientation.
MAC_DROP = int(float(NERVE_MAC_DIST) * 0.1)
MAC_ANGLE = math.degrees(math.atan(float(MAC_DROP) / float(NERVE_MAC_DIST)))

# the (x,y) coordinate of the optic nerve on the heatmap canvas
# note: (NERVE_COORD, NERVE_COORD) is the coordinate to use.
# note: this canvas will be necessarily huge because the photos have large
#       borders which cannot be stripped until after processing is finished
NERVE_COORD = int(1000 * SIZE_MULTIPLIER)

DRAW_QUADS = False
QUAD_BOX_SIZE = (int(200 * SIZE_MULTIPLIER), int(200 * SIZE_MULTIPLIER))

# trim - the resulting image will have large black borders, so cut this
# much off each side (measured in pixels)
SUPERIOR=0
NASAL=1
INFERIOR=2
TEMPORAL=3
TRIM = [int(450 * SIZE_MULTIPLIER),
        int(600 * SIZE_MULTIPLIER),
        int(450 * SIZE_MULTIPLIER),
        int(300 * SIZE_MULTIPLIER)]

# directory structure for images
IMAGE_SUBDIR = "image"
LESION_SUBDIR = "label"
LESION_LABELS = { "EX": "Exudates",\
                  "HE": "Haemorrhages",\
                  "MA": "Microaneurysms",\
                  "SE": "Cotton Wool Spots",\
                  "IRH": "Intraretinal Haemorrhages",\
                  "IRMA": "Intraretinal Microvascular Abnormalities",\
                  "NV": "Neovascularisation",\
                  "NVD": "New Vessels at the Disc",\
                  "NVE": "New Vessels Elsewhere",\
                  "VB": "Venous Beading",\
                  "ALL": "All Retinopathy" }

VESSEL_LABELS = { "A": "Arterioles",\
                  "V": "Venules",\
                  "ALL_AV": "All Vessels" }

class CoordsData:
    filename = None
    nerve_xy = None
    mac_xy = None

    def __init__(self, filename, nerve_xy, mac_xy):
        self.filename = filename
        self.nerve_xy = nerve_xy
        self.mac_xy = mac_xy

    def showImage(self):
        image = cv2.imread(self.filename)
        cv2.imshow(self.filename, image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def __repr__(self):
        return "[filename=" + self.filename + \
               ", nerve_xy=(" + str(self.nerve_xy) + ")" + \
               ", mac_xy=(" + str(self.mac_xy) + ")]"

def parseCoordsFile(filename, image_dir):
    coords = list()

    with open(filename) as csvfile:
        coords_data = csv.reader(csvfile, delimiter=',')
        for index, row in enumerate(coords_data):
            # ignore the first row - header
            if (index == 0):
                continue

            coords.append(CoordsData(os.path.join(image_dir, IMAGE_SUBDIR, row[0]),
                          (int(row[1]), int(row[2])),
                          (int(row[3]), int(row[4]))))

    return coords

def trimImageArrays(image, labels, scale_lesion_counts=False):
    orig_x_len = len(image[0][0])
    orig_y_len = len(image[0][0][0])
    x_len = orig_x_len - TRIM[NASAL] - TRIM[TEMPORAL]
    y_len = orig_y_len - TRIM[SUPERIOR] - TRIM[INFERIOR]

    trimmed = np.zeros((3, len(labels) + 1, x_len, y_len), dtype=np.uint32)

    for i, l in enumerate(labels):
        trimmed[RIGHT_EYE][i] = image[RIGHT_EYE][i][TRIM[SUPERIOR]:orig_x_len-TRIM[INFERIOR],\
                                                    TRIM[TEMPORAL]:orig_y_len-TRIM[NASAL]]
        trimmed[LEFT_EYE][i] = image[LEFT_EYE][i][TRIM[SUPERIOR]:orig_x_len-TRIM[INFERIOR],\
                                                  TRIM[NASAL]:orig_y_len-TRIM[TEMPORAL]]
        trimmed[BOTH_EYES][i] = image[BOTH_EYES][i][TRIM[SUPERIOR]:orig_x_len-TRIM[INFERIOR],\
                                                    TRIM[TEMPORAL]:orig_y_len-TRIM[NASAL]]

        # scale
        if scale_lesion_counts:
            for eye in (RIGHT_EYE, LEFT_EYE, BOTH_EYES):
                heatmap_scale = 255.0 / float(max(1, trimmed[eye][i].max()))
                trimmed[eye][i] = trimmed[eye][i] * heatmap_scale

    return trimmed

def printUsage():
    print("Usage: " + sys.argv[0] + " <coordinates_csv> <image_dir> <data_type (dr,vessels)> [<outdir=heatmaps> [<outfile_suffix>]]")

def addText(image, position, text):
    cv2.putText(image, text, position, cv2.FONT_HERSHEY_DUPLEX, 1, (255,255,255), 2)
    return image

# Scale the image such that the distance between the nerve
# and macula is NERVE_MAC_DIST. Return the scaled (x,y) position
# of the nerve in the scaled image, as well as the scaling factor
# and rotation required.
# @param image_data CoordsData object
def scaleImage(image_data):
    # Calculate the distace from the nerve to the mac. Ye Olde Pythagoras.
    x = abs(image_data.nerve_xy[0] - image_data.mac_xy[0])
    y = abs(image_data.nerve_xy[1] - image_data.mac_xy[1])
    orig_dist = int(math.sqrt((x*x) + (y*y)))

    if (orig_dist == 0):
        print("ERROR: invalid tagging for image (ignoring): " + image_data.filename)
        return None, None

    # Calculate the angle from the nerve to the mac
    angle = math.degrees(math.atan(float(y) / float(x)))

    # Image rotation required (in degrees)
    rotation = MAC_ANGLE - angle

    # left eyes rotate the opposite direction
    if rightOrLeft(image_data) == LEFT_EYE:
        rotation = angle - MAC_ANGLE

    scaling_factor =  float(NERVE_MAC_DIST) / float(orig_dist)

    new_nerve_xy = (int(float(image_data.nerve_xy[0]) * scaling_factor),
                    int(float(image_data.nerve_xy[1]) * scaling_factor))

    return new_nerve_xy, scaling_factor, rotation

# @param image_data CoordsData object
def rightOrLeft(image_data):
    if (image_data.nerve_xy[0] > image_data.mac_xy[0]):
        return RIGHT_EYE
    return LEFT_EYE

if __name__ == '__main__':
    if (len(sys.argv) not in [4,5,6]):
        printUsage()
        sys.exit(1)

    cli_args_valid = True

    coords_csv = os.path.abspath(sys.argv[1])
    if (not os.path.exists(coords_csv)):
        print("ERROR: coordinates_csv file \"" + coords_csv + "\" does not exist")
        cli_args_valid = False
    
    image_dir = os.path.abspath(sys.argv[2])
    if (not os.path.exists(image_dir)):
        print("ERROR: image_dir path \"" + image_dir + "\" does not exist")
        cli_args_valid = False

    data_type = sys.argv[3]
    labels = LESION_LABELS
    if data_type == "vessels":
        labels = VESSEL_LABELS
    elif data_type != "dr":
        print("ERROR: data_type must be 'dr' or 'vessels'")
        cli_args_valid = False

    # all location data is combined into a composite label. This is the index
    # of that label in the labels hashmap keys
    composite_label = len(labels) - 1

    outdir = "heatmaps"
    if len(sys.argv) > 4:
        outdir = sys.argv[4]
    os.makedirs(outdir, exist_ok=True)

    out_suffix = ""
    if len(sys.argv) > 5:
        out_suffix = "_" + sys.argv[5]

    if (not cli_args_valid):
        sys.exit(1)

    print("Using CSV file \"" + coords_csv + "\"")
    print("with image dir \"" + image_dir + "\"")

    coords_data = parseCoordsFile(coords_csv, image_dir)

    # Initialise the data array (nerve at (NERVE_COORD,NERVE_COORD) which
    # is the middle of our matrix
    # stored as [side][lesion][x][y]
    heatmap_data = np.zeros((3, len(labels) + 1, NERVE_COORD * 2, NERVE_COORD * 2), dtype=np.uint16)

    print("Extracting lesion data", end='', flush=True)
    for r, record in enumerate(coords_data):
        if not os.path.exists(record.filename):
            print("ERROR: image does not exist (ignoring): " + record.filename)
            continue

        # print a dot for each image - gives the user an idea of how we're tracking
        print(".", end='', flush=True)

        side = rightOrLeft(record)

        # Calculate the scaling factor and scaled nerve position. This determines
        # how to scale the lesion coordinates, and how far to translate them to
        # make sure everything lines up.
        nerve_xy_scaled, scaling_factor, rotation = scaleImage(record)

        if (nerve_xy_scaled == None or scaling_factor == None):
            print("ERROR: ignoring file: " + record.filename)
            continue

        # Load the lesion file(s)
        for index, lesion in enumerate(labels):
            # "ALL" is generated by us from the other lesion types
            if index == composite_label:
                continue

            lesion_image_path = os.path.join(image_dir, LESION_SUBDIR, lesion, os.path.split(record.filename)[1])

            # lesion files are .tif or .png, depending on the source
            # label files can have a few different naming conventions and formats. Try them all.
            path_valid = False
            for suffix in (".tif", ".png", "_AV.tif"):
                label_path = os.path.splitext(lesion_image_path)[0] + suffix

                if os.path.exists(label_path):
                    lesion_image_path = label_path
                    path_valid = True
                    break

            if not path_valid:
                # no valid file found
                print("ERROR: label file does not exist (ignoring): " + os.path.split(lesion_image_path)[0])
                continue

            # load the image...
            lesion_orig = cv2.imread(lesion_image_path, 0)

            # ...convert to binary (for ease of processing)...
            lesion_orig = np.where(lesion_orig > 0, 1, 0).astype(np.uint8)

            # ...scale it...
            lesion_scaled = cv2.resize(lesion_orig, None,
                                       fx=scaling_factor,
                                       fy=scaling_factor)

            # ...rotate it...
            rot_matrix = cv2.getRotationMatrix2D(nerve_xy_scaled, rotation, 1.0)
            img_dims = (len(lesion_scaled[0]), len(lesion_scaled))
            lesion_scaled = cv2.warpAffine(lesion_scaled, rot_matrix, img_dims)

            # ...and mark it in our heatmap matrix
            y_from = NERVE_COORD - nerve_xy_scaled[1]
            y_to = y_from + len(lesion_scaled)
            x_from = NERVE_COORD - nerve_xy_scaled[0]
            x_to = x_from + len(lesion_scaled[0])

            if (x_from < 0 or y_from < 0 or x_to > len(heatmap_data[side][index]) or y_to > len(heatmap_data[side][index][0])):
                print("ERROR:", lesion, "mapping outside of bounds (ignoring):", os.path.basename(record.filename))
                continue

            heatmap_data[side][index][y_from:y_to, x_from:x_to] += lesion_scaled
            heatmap_data[side][composite_label][y_from:y_to, x_from:x_to] += lesion_scaled

            # add data to our composite heatmaps as well - represented as right side,
            # so need to mirror left data.
            if (side == LEFT_EYE):
                lesion_scaled = np.fliplr(lesion_scaled)
                x_from = NERVE_COORD - len(lesion_scaled[0]) + nerve_xy_scaled[0]
                x_to = x_from + len(lesion_scaled[0])
            heatmap_data[BOTH_EYES][index][y_from:y_to, x_from:x_to] += lesion_scaled
            heatmap_data[BOTH_EYES][composite_label][y_from:y_to, x_from:x_to] += lesion_scaled

            # if we are saving progress for each image, do that here
            if SAVE_INTERMEDIATE_DATA:
                frame_number = f'{r:04}'
                trimmed = trimImageArrays(heatmap_data, labels, SCALE_LESION_COUNTS)
                for i, l in enumerate(labels):
                    fname = os.path.join(outdir, INTERMEDIATE_DIR, "lesion_count_" + SIDE_LABELS[BOTH_EYES] + "_" + l + out_suffix + "_" + frame_number + ".csv")
                    np.savetxt(fname, trimmed[BOTH_EYES][i], fmt="%i", delimiter=",")

    print("done")

    # write the heatmap data to file
    trimmed = trimImageArrays(heatmap_data, labels, SCALE_LESION_COUNTS)

    for side in [RIGHT_EYE, LEFT_EYE, BOTH_EYES]:
        for i, l in enumerate(labels):
            print("Generating", ("right", "left", "composite")[side], labels[l], "CSV file")
            np.savetxt(os.path.join(outdir, "lesion_count_" + SIDE_LABELS[side] + "_" + l + out_suffix + ".csv"), trimmed[side][i], fmt="%i", delimiter=",")

    # with a README
    with open("README_csv.txt", "w") as f:
        print("How to interpret the CSV files", file=f)
        print("==============================", file=f)
        print("", file=f)
        print("Each file contains the number of lesions found at each pixel co-ordinate.", file=f)
        print("Note that this uses the screen standard of (0, 0) located at the top left corner.", file=f)
        print("", file=f)
        print("For the right eye and composite images:", file=f)
        print("  Optic nerve position = (", NERVE_COORD - TRIM[TEMPORAL], ",", NERVE_COORD - TRIM[SUPERIOR], ")", file=f)
        print("  Macular position = (", NERVE_COORD - TRIM[TEMPORAL] - NERVE_MAC_DIST, ",", NERVE_COORD - TRIM[SUPERIOR] + MAC_DROP, ")", file=f)
        print("", file=f)
        print("For the left eye:", file=f)
        print("  Optic nerve position = (", NERVE_COORD - TRIM[NASAL], ",", NERVE_COORD - TRIM[SUPERIOR], ")", file=f)
        print("  Macular position = (", NERVE_COORD - TRIM[NASAL] + NERVE_MAC_DIST, ",", NERVE_COORD - TRIM[SUPERIOR] + MAC_DROP, ")", file=f)

    # We now have a giant array with count values. Convert to a uint8 array with
    # normalised values.
    heatmap_image = np.zeros((3, len(labels) + 1, NERVE_COORD * 2, NERVE_COORD * 2), dtype=np.uint8)
    for side in [RIGHT_EYE, LEFT_EYE, BOTH_EYES]:
        for index, lesion in enumerate(labels):
            print("Generating", ("right", "left", "composite")[side], labels[lesion], "heatmap...", end='')
            heatmap_scale = 255.0 / float(max(1, heatmap_data[side][index].max()))
            heatmap_image[side][index] = heatmap_data[side][index] * heatmap_scale

            # add the optic nerve visualisation
            cv2.circle(heatmap_image[side][index], (NERVE_COORD, NERVE_COORD), int(45 * SIZE_MULTIPLIER), (255), 2)
            cv2.circle(heatmap_image[side][index], (NERVE_COORD, NERVE_COORD), int(30 * SIZE_MULTIPLIER), (255), 2)
            cv2.circle(heatmap_image[side][index], (NERVE_COORD, NERVE_COORD), int(15 * SIZE_MULTIPLIER), (255), 2)

            # and the macula
            mac_coord = (NERVE_COORD - ((1, -1, 1)[side] * NERVE_MAC_DIST),
                        NERVE_COORD + MAC_DROP)
            cv2.circle(heatmap_image[side][index],
                       mac_coord,
                       int(25 * SIZE_MULTIPLIER), (255), 2)

            # also draw in the quads used for stats
            if (DRAW_QUADS):
                cv2.line(heatmap_image[side][index],
                         (mac_coord[0] - QUAD_BOX_SIZE[0], mac_coord[1]),
                         (mac_coord[0] + QUAD_BOX_SIZE[0], mac_coord[1]),
                         255, 2)
                cv2.line(heatmap_image[side][index],
                         (mac_coord[0], mac_coord[1] - QUAD_BOX_SIZE[1]),
                         (mac_coord[0], mac_coord[1] + QUAD_BOX_SIZE[1]),
                         255, 2)
                cv2.rectangle(heatmap_image[side][index],
                              (mac_coord[0] - QUAD_BOX_SIZE[0], mac_coord[1] - QUAD_BOX_SIZE[1]),
                              (mac_coord[0] + QUAD_BOX_SIZE[0], mac_coord[1] + QUAD_BOX_SIZE[1]),
                              255, 2)

            print("done")

    # trim the black edges from the images
    trimmed = trimImageArrays(heatmap_image, labels)

    # add some descriptive text
    if ADD_LABELS:
        for i, l in enumerate(labels):
            addText(trimmed[RIGHT_EYE][i], (30,50), "Right Eye - " + labels[l])
            addText(trimmed[LEFT_EYE][i], (30,50), "Left Eye - " + labels[l])
            addText(trimmed[BOTH_EYES][i], (30,50), "Combined - " + labels[l])

    # and we're done! put all the heatmaps together
    stacks = []
    for index, lesion in enumerate(labels):
        s = np.hstack((trimmed[RIGHT_EYE][index],\
                       trimmed[LEFT_EYE][index],\
                       trimmed[BOTH_EYES][index]))
        cv2.imwrite(os.path.join(outdir, "heatmap_" + lesion + out_suffix + ".png"), s.astype(np.uint8))
        stacks.append(s)

    if BIG_STACK_IMAGE:
        composite = None
        for s in stacks:
            if (composite is None):
                composite = s
            else:
                composite = np.vstack((composite, s))
        cv2.imwrite(os.path.join(outdir, "heatmap" + out_suffix + ".png"), composite.astype(np.uint8))

    if PREVIEW:
        # for display purposes, shrink down the image to fit on (most) screens
        stack = cv2.resize(stacks[composite_label], (1500, 500))
        cv2.imshow("heatmap", stack)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

# EOF
