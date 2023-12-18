# Extract the images and arteriole/venule annotations from the relevant
# datasets. This places everything in the correct folder structure to allow
# scripts to analyse them.

import cv2
import numpy as np
import os
import shutil
import sys

def split_image(image_path):
    im = cv2.imread(image_path)

    # replace white pixels with black
    # this will remove unknown vessels (RITE) and make the background black (IOSTAR)
    im[np.where((im==[255,255,255]).all(axis=2))] = [0,0,0]

    # where "shades" of blue and red are used (thanks IOSTAR...) fiddle with HSV
    im = cv2.cvtColor(im, cv2.COLOR_RGB2HSV)
    im[:,:,1] = 255 # max out Saturation
    im = cv2.cvtColor(im, cv2.COLOR_HSV2RGB)

    blue = np.array([0,0,1]).reshape((1,3))
    blue = cv2.transform(im, blue)
    red = np.array([1,0,0]).reshape((1,3))
    red = cv2.transform(im, red)
    green = np.array([0,1,0]).reshape((1,3))
    green = cv2.transform(im, green)

    # Green pixels mean there are arteries AND veins in that position.
    veins = blue + green
    arteries = red + green

    return veins, arteries
    

if __name__ == '__main__':
    if (len(sys.argv) != 4):
        print("Usage:", __file__, "<label_dir>", "<image_dir>", "<output_dir>")
        sys.exit(1)

    # validate command line arguments
    label_dir = sys.argv[1]
    if not os.path.isdir(label_dir):
        print("ERROR: label_dir is not a valid directory:", label_dir, file=sys.stderr)
        sys.exit(1)

    image_dir = sys.argv[2]
    if not os.path.isdir(image_dir):
        print("ERROR: image_dir is not a valid directory:", image_dir, file=sys.stderr)
        sys.exit(1)

    output_dir = sys.argv[3]
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # make directories
    labeldir_a = os.path.join(output_dir, "label", "A")
    labeldir_v = os.path.join(output_dir, "label", "V")
    imgdir = os.path.join(output_dir, "image")
    for d in (labeldir_a, labeldir_v, imgdir):
        if not os.path.exists(d):
            os.makedirs(d)

    # get all of the files in this directory
    dir_files = []
    for root, dirs, files in os.walk(label_dir):
        for f in files:
            file_ext = os.path.splitext(f)[1]
            if file_ext in (".tif", ".png"):
                dir_files.append(os.path.join(root, f))

    # extract the annotations
    print("Extracting labels...")
    for f in dir_files:
        print(" ", f)
        arteries, veins = split_image(f)
        cv2.imwrite(os.path.join(labeldir_a, os.path.basename(f)), arteries)
        cv2.imwrite(os.path.join(labeldir_v, os.path.basename(f)), veins)
    print("done")
    print()

    # and copy over the images
    print("Copying images...")
    for root, dirs, files in os.walk(image_dir):
        for f in files:
            print(" ", f)
            shutil.copy(os.path.join(root, f), imgdir)
    print("done")
    print()

    print("All done! Have a nice day :)")

# EOF
