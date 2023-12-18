# Extract images and diabetic retinopathy feature annotations from the DDR
# dataset, by Li et al. (2019). This puts everything in the correct folder
# structure to allow analysis by other scripts.

import glob
import os
import shutil
import sys

LESIONS=('EX', 'HE', 'MA', 'SE')
IMAGEDIR="image"
LABELDIR="label"

def printUsage():
    print("Usage: " + sys.argv[0] + " <unzipped_dir> <output_dir> [<overwrite=False>]", file=sys.stderr)
    print("  unzipped_dir should be *DDR-dataset* containing a folder called *lesion_segmentation*", file=sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        printUsage()
        sys.exit(1)

    # source directory
    unzipped_dir = sys.argv[1]
    if not os.path.isdir(unzipped_dir):
        print("ERROR: unzipped_dir does not exist: " + unzipped_dir, file=sys.stderr)
        printUsage()
        sys.exit(1)

    # destination folder
    output_dir = sys.argv[2]
    overwrite = False
    if len(sys.argv) > 3:
        if sys.argv[3].lower() == "true":
            overwrite = True
        elif sys.argv[3].lower() == "false":
            overwrite = False
        else:
            print("ERROR: invalid overwrite value (" + sys.argv[3] + "): should be true or false", file=sys.stderr)
            printUsage()
            sys.exit(1)

    # make all of the destination subdirectories
    try:
        os.makedirs(output_dir, exist_ok=overwrite)
        subdirs = (IMAGEDIR, LABELDIR)
        for s in subdirs:
            os.makedirs(os.path.join(output_dir, s), exist_ok=overwrite)
        for l in LESIONS:
            os.makedirs(os.path.join(output_dir, LABELDIR, l), exist_ok=overwrite)
    except OSError:
        print("ERROR: output_dir already exists (not overwriting): " + output_dir, file=sys.stderr)
        printUsage()
        sys.exit(1)

    print("unzipped_dir: " + unzipped_dir)
    print("output_dir: " + output_dir)

    # there should be a folder called "lesion_segmentation" here, which contains
    # all the data we need
    data_dir = os.path.join(unzipped_dir, "lesion_segmentation")
    if not os.path.isdir(data_dir):
        print("ERROR: subdirectory does not exist - did you download the correct zip file? " + data_dir, file=sys.stderr)
        printUsage()
        sys.exit(1)

    # Data is stored in three categories: test, train, and valid. We don't need
    # to split it this way, so treat it all the same.
    print("Extracting files...", end='')
    copied = 0
    categories = ('test', 'train', 'valid')
    for cat in categories:
        cat_dir = os.path.join(data_dir, cat)
        if not os.path.isdir(cat_dir):
            print("ERROR: subdirectory does not exist - did you download the correct zip file? " + data_dir, file=sys.stderr)
            printUsage()
            sys.exit(1)

        # copy each of the images
        img_dir_src = os.path.join(cat_dir, IMAGEDIR)
        img_dir_dst = os.path.join(output_dir, IMAGEDIR)
        for f in glob.glob(os.path.join(img_dir_src, '*.*')):
            shutil.copy(f, img_dir_dst)
            copied += 1
            print(".", end='', flush=True)

        for l in LESIONS:
            # copy each of the label files
            label_dir_src = os.path.join(cat_dir, LABELDIR, l)
            label_dir_dst = os.path.join(output_dir, LABELDIR, l)
            for f in glob.glob(os.path.join(label_dir_src, '*.*')):
                shutil.copy(f, label_dir_dst)
                print(".", end='', flush=True)

    print("done")
    print(str(copied) + " images copied")

# EOF
