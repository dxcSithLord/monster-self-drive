# ML Models for Object Detection

This directory contains TensorFlow Lite models for object detection.

## Required Models

Download the following models for Coral TPU inference:

### MobileNet SSD v2 (COCO) - Recommended

```bash
# Download Edge TPU compiled model
wget https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite

# Download labels
wget https://github.com/google-coral/test_data/raw/master/coco_labels.txt
```

### Alternative Models

| Model | Download | Use Case |
|-------|----------|----------|
| EfficientDet-Lite0 | [Link](https://coral.ai/models/object-detection/) | Higher accuracy |
| MobileNet v2 | [Link](https://coral.ai/models/image-classification/) | Classification only |

## Model Compatibility

- **Coral TPU**: Use `*_edgetpu.tflite` models (compiled for Edge TPU)
- **CPU Fallback**: Use standard `*.tflite` models (uncompiled)

The code automatically selects the appropriate model based on filename.

## Directory Structure

```
models/
├── README.md                                              # This file
├── ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite # Coral TPU model
├── ssd_mobilenet_v2_coco_quant_postprocess.tflite         # CPU fallback
└── coco_labels.txt                                        # Class labels
```

## COCO Classes (90 objects)

The models detect these object categories:
- Person, bicycle, car, motorcycle, airplane, bus, train, truck, boat
- Traffic light, fire hydrant, stop sign, parking meter, bench
- Bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe
- And many more household items, food, furniture, etc.

See `coco_labels.txt` for the complete list.
