# Diabetic Retinopathy Feature Localisationo

The commands here assume you are using Powershell on Windows. Though not
explicitly tested, the scripts should work on Mac and Linux systems but the
command line syntax may need to be changed.

You will need to install Python 3 to run these commands. To install dependencies,
run the following command:

> `pip install -r requirements.txt`

## Data Preparation

This project uses the data from the [DDR](https://github.com/nkicsl/DDR-dataset)
dataset by Li et al. (2019), the [RITE](https://medicine.uiowa.edu/eye/rite-dataset)
dataset by Hu et al. (2013), and the [IOSTAR](https://www.idiap.ch/software/bob/docs/bob/bob.db.iostar/stable/)
dataset by Zhang et al (2016). We need to do some preparation first before we can
do any analysis.

### DDR Dataset

The DDR dataset comprises of multiple zip files, however all of the annotations
are in the *DDR-dataset.zip.001.zip* file. Download this file and unzip it
somewhere - I'll assume it's in your Downloads folder. This should create a
file called *DDR-dataset.zip.010*. Rename this to *DDR-dataset.zip.010.zip* (add
*.zip* to the end of the filename) and unzip it again. Again, I'll assume this
is in your Downloads folder. This should create a folder called *DDR-dataset*,
which contains all the data we need To use it, but it's stored in a bunch of
sub-directories, so we need to consolidate it into one directory. Before the
images can be extracted, make sure the "test", "train" and "valid"
subdirectories contain "image" and "label" folders - you may need to rename
the "label" folder in "valid". Finally, run the following python script,
assuming the data is in your Downloads folder:

> `python .\extract_dr.py "${env:USERPROFILE}\Downloads\DDR-dataset" dataset_dr`

This will put all of the images and annotations into the *dataset_dr* folder.

### RITE Dataset

This dataset is downloaded as a single zip file: *AV_groundTruth.zip*. As for
DDR, I'll assume you've downloaded and unzipped this in your Downloads folder.
You should now have a folder in your downloads called *AV_groundTruth*.

To extract the arteriole and venule ground truth images, run the following
two commands:

> `python .\extract_vessels.py "${env:USERPROFILE}\Downloads\AV_groundTruth\training\av" "${env:USERPROFILE}\Downloads\AV_groundTruth\training\images" dataset_av`

and

> `python .\extract_vessels.py "${env:USERPROFILE}\Downloads\AV_groundTruth\test\av"  "${env:USERPROFILE}\Downloads\AV_groundTruth\test\images" dataset_av`

This will put all of the annotations in the *dataset_av* folder.

### IOSTAR Dataset

This dataset is also in a single zip file: *IOSTAR-Vessel-Segmentation-Dataset-2018.zip*.
Unzip this somewhere, again I'll assume it's in your downloads folder. You
should now have a folder in your downloads called *IOSTAR-Vessel-Segmentation-Dataset*.

To extract the arteriole and venule ground truth images, run the following
command:

> `python .\extract_vessels.py "${env:USERPROFILE}\Downloads\IOSTAR Vessel Segmentation Dataset\AV_GT"  "${env:USERPROFILE}\Downloads\IOSTAR Vessel Segmentation Dataset\image" dataset_av`

This will put all of the annotations in the *dataset_av* folder.

## Additional Annotations

We have created additional annotations for images in the DDR datates for
neovascularisation, venous beading, and intraretinal microvascular
abnormalities. These files are too large to include in the repository, so please
contact Tim Murphy <tim@murphy.org> for access.

Note: this software can be used without these additional annotations if you do
not want or need them. This will generate a lot of warnings about label files
not existing but these can be ignored.

## Image Nerve and Fovea Location

Note: this step has been done for you with results stored in *coordinates_dr.csv*
and *coordinates_vessels.csv* but instructions have been included here for
completeness.

Image annotations cannot be directly compared in their raw form due to
differences in centration, rotation, and field of view. To normalise these
data, we can rotate, translate and resize the images so that all optic discs
and foveae are co-located. To do this, we need to know the position of these
anatomical features in each image, which requires manual localisation.

To mark the location of these features, run the following script:

> `foreach ($i in (gci dataset_dr\image\*.jpg)) { python .\image_click.py coordinates_dr.csv $i }`

(Note: this needs to be done in a loop as there are too many image files for
Powershell to handle. This should not be a problem for Mac or Linux users).

To add the locations, first click on the centre of the optic disc, then on the
centre of the fovea. After the second click, the locations will be printed to
the terminal and written to the file. If you make a mistake, you can annotate
again and remove the first entry from the output file later, or remove the
entry from the output file and run the script again.

This process can take a very long time, so you can stop and start the script
as needed. Images which have already been processed will be skipped.

Repeat the process for the vessels dataset:

> `foreach ($i in (gci dataset_av\image\*.jpg)) { python .\image_click.py coordinates_av.csv $i }`

## Heatmap Generation

The following command will convert the ground truth data to heatmaps:

> `python .\create_heatmap.py .\coordinates_dr.csv .\dataset_dr dr`

This will extract heatmap data for each feature and store the feature count
for each pixel location (default canvas size 1100 x 1100) in CSV format in the
*heatmap* folder. Heatmaps for each feature will also be created here.

Repeat the process for vessels:

> `python .\create_heatmap.py .\coordinates_av.csv .\dataset_av vessels`

The raw feature count data can be used by other software to create coloured
heatmaps or to do other analysis.
