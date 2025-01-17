import os
import time
from shutil import rmtree

import cv2
import numpy as np

from src.components.MaskOrientGenerator.MaskOrientGenerator import MaskOrientGenerator
from src.transformers.ComponentFactory import *
from src.util.sender import Sender

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Transformer:
    ref_cache = {}

    def __init__(self, boundingBoxFactory, alignerFactory, balderFactory, caching=True, pass_through=False):
        self.caching = caching
        self.pass_through = pass_through

        self.boundingBoxFactory = boundingBoxFactory
        self.alignerFactory = alignerFactory
        self.balderFactory = balderFactory

        self.appearance_ref = None
        self.shape_ref = None
        self.structure_ref = None

        self.sender = Sender()
        self.MOGenerator = MaskOrientGenerator()

    def set_appearance_ref(self, ref: np.ndarray):
        self.appearance_ref = ref

    def set_shape_ref(self, ref: np.ndarray):
        self.shape_ref = ref

    def set_structure_ref(self, ref: np.ndarray):
        self.structure_ref = ref

    def transform(self, original_image: np.ndarray) -> np.ndarray:
        # original_image : 1920 x 1080
        # return : 1920 x 1080

        if self.pass_through:
            if self.appearance_ref is None and self.shape_ref is None and self.structure_ref is None:
                return original_image

        boundingBox = self.boundingBoxFactory(original_image)

        try:
            aligner = self.alignerFactory(boundingBox)
        except ValueError as v:
            print("valueError:", v)
            return original_image
        except Exception as e:
            print(e)
            return original_image

        balder = self.balderFactory()

        src = self._src_preprocess(aligner, balder)

        appearance_ref, shape_ref, structure_ref = None, None, None
        if self.appearance_ref is not None:
            appearance_ref = self._ref_preprocess(self.appearance_ref)

        if self.shape_ref is not None:
            shape_ref = self._ref_preprocess(self.shape_ref)

        if self.structure_ref is not None:
            structure_ref = self._ref_preprocess(self.structure_ref)

        # Appearance
        appearance_mask = src['mask'] if appearance_ref is None else appearance_ref['mask']
        appearance_img = src['img_origin'] if appearance_ref is None else appearance_ref['img']

        # Shape
        shape_mask = src['mask'] if shape_ref is None else shape_ref['mask']

        # Structure
        orient = src['orient'] if structure_ref is None else structure_ref['orient']

        # App : appearance_ref
        # Shape : shape_ref
        # Structure : structure_ref
        # None인 항목은 src의 속성을 유지하도록 변환
        datas = {
            'label_ref': appearance_mask,  # appearance
            'label_tag': shape_mask,  # shape

            'orient_mask': shape_mask,  # structure ref mask
            'orient_tag': orient,  # src orient ???????
            'orient_ref': orient,  # structure ref orient

            'image_ref': appearance_img,  # appearance
            'image_tag': src['img_bald'],  # src
        }
        generated: np.ndarray = self.sender.send_and_recv(datas)

        generated = balder.scaler.scale_backward(generated)
        generated = aligner.align_backward(generated)
        ret = boundingBox.set_origin_patch(generated)
        return ret

    def _ref_preprocess(self, ref_img):
        if self.caching:
            key = str(ref_img)
            if key in Transformer.ref_cache.keys():
                print('ref cache hit')
                return Transformer.ref_cache[key]

        aligner = self.alignerFactory(self.boundingBoxFactory(ref_img))

        scaled_ref = Scaler((aligner.align_forward())).scale_forward()
        mask_ref, orient_ref = self.MOGenerator.generate(scaled_ref)

        ret = {
            'img': scaled_ref,
            'mask': mask_ref,
            'orient': orient_ref
        }

        if self.caching:
            Transformer.ref_cache[key] = ret
        return ret

    def _src_preprocess(self, aligner, bald):
        aligned_face_patch_src = aligner.align_forward()

        # bald
        balded_src = bald.run(aligned_face_patch_src)

        src_origin = Scaler(aligned_face_patch_src).scale_forward()
        mask_src, orient_src = self.MOGenerator.generate(src_origin)

        ret = {
            'img_origin': src_origin,
            'img_bald': balded_src,
            'mask': mask_src,
            'orient': orient_src
        }
        return ret


def getTransformer() -> Transformer:
    return Transformer(boundingBoxFactory=BoundingBoxFactory,
                       alignerFactory=AlignerWingFactory,
                       balderFactory=BalderFactory,
                       pass_through=True, )
