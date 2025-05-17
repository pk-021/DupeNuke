import argparse
import sys
from os import listdir
from os.path import isfile, join
from typing import Dict, List, Tuple
from collections import defaultdict

import imagehash
import numpy as np
from PIL import Image





def calculate_signature(image_file: str, hash_size: int) -> np.ndarray:
    """ 
    Calculate the dhash signature of a given file
    
    Args:
        image_file: the image (path as string) to calculate the signature for
        hash_size: hash size to use, signatures will be of length hash_size^2
    
    Returns:
        Image signature as Numpy n-dimensional array or None if the file is not a PIL recognized image
    """
    pil_image = Image.open(image_file).convert("L").resize(
                        (hash_size+1, hash_size),
                        Image.Resampling.LANCZOS)
    dhash = imagehash.dhash(pil_image, hash_size)
    signature = dhash.hash.flatten()
    pil_image.close()
    return signature

        
def find_near_duplicates(input_dir: str, threshold: float, hash_size: int, bands: int) -> List[Tuple[str, str, float]]:
    """
    Find near-duplicate images
    
    Args:
        input_dir: Directory with images to check
        threshold: Images with a similarity ratio >= threshold will be considered near-duplicates
        hash_size: Hash size to use, signatures will be of length hash_size^2
        bands: The number of bands to use in the locality sensitve hashing process
        
    Returns:
        A list of near-duplicates found. Near duplicates are encoded as a triple: (filename_A, filename_B, similarity)
    """
    rows: int = int(hash_size**2/bands)
    signatures = dict()
    hash_buckets_list: List[Dict[str, List[str]]] = [dict() for _ in range(bands)]
    
    # Build a list of candidate files in given input_dir
    file_list = [join(input_dir, f) for f in listdir(input_dir) if isfile(join(input_dir, f))]

    # Iterate through all files in input directory
    for fh in file_list:
        try:
            signature = calculate_signature(fh, hash_size)
        except IOError:
            print("Not a PIL image encountered")
            # Not a PIL image, skip this file
            continue

        # Keep track of each image's signature
        signatures[fh] = np.packbits(signature)
        
        # Locality Sensitive Hashing
        for i in range(bands):
            signature_band = signature[i*rows:(i+1)*rows]
            signature_band_bytes = signature_band.tobytes()
            if signature_band_bytes not in hash_buckets_list[i]:
                hash_buckets_list[i][signature_band_bytes] = list()
            hash_buckets_list[i][signature_band_bytes].append(fh)

    # Build candidate pairs based on bucket membership
    candidate_pairs = set()
    for hash_buckets in hash_buckets_list:
        for hash_bucket in hash_buckets.values():
            if len(hash_bucket) > 1:
                hash_bucket = sorted(hash_bucket)
                for i in range(len(hash_bucket)):
                    for j in range(i+1, len(hash_bucket)):
                        candidate_pairs.add(
                            tuple([hash_bucket[i],hash_bucket[j]])
                        )

    # Check candidate pairs for similarity
    near_duplicates = list()
    for cpa, cpb in candidate_pairs:
        hd = int(np.bitwise_xor(
                np.unpackbits(signatures[cpa]), 
                np.unpackbits(signatures[cpb])
        ).sum())

        similarity = (hash_size**2 - hd) / hash_size**2
        if similarity > threshold:
            near_duplicates.append((cpa, cpb, similarity))
            
    # Sort near-duplicates by descending similarity and return
    near_duplicates.sort(key=lambda x:x[2], reverse=True)
    return near_duplicates


def group_similar_images(near_duplicates):
    """
    Groups images based on near-duplicate pairs.

    Args:
        near_duplicates: List of tuples (imgA, imgB, similarity)

    Returns:
        List of lists, where each inner list is a group of similar images.
    """
    parent = {}

    # Initialize parent pointers for all images found in pairs
    def make_set(x):
        if x not in parent:
            parent[x] = x

    # Find root leader of group containing x
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    # Union groups of x and y
    def union(x, y):
        root_x = find(x)
        root_y = find(y)
        if root_x != root_y:
            parent[root_y] = root_x

    # Initialize sets for all images in near_duplicates
    for a, b, _ in near_duplicates:
        make_set(a)
        make_set(b)

    # Union similar image pairs
    for a, b, _ in near_duplicates:
        union(a, b)

    # Group images by their root leader
    clusters = defaultdict(list)
    for img in parent:
        root = find(img)
        clusters[root].append(img)

    return list(clusters.values())


def main(argv):
    # Argument parser
    parser = argparse.ArgumentParser(description="Efficient detection of near-duplicate images using locality sensitive hashing")
    parser.add_argument("-i", "--inputdir", type=str, default="", help="directory containing images to check")
    parser.add_argument("-t", "--threshold", type=float, default=0.9, help="similarity threshold")
    parser.add_argument("-s", "--hash-size", type=int, default=16, help="hash size to use, signature length = hash_size^2", dest="hash_size")
    parser.add_argument("-b", "--bands", type=int, default=16, help="number of bands")

    args = parser.parse_args()
    input_dir = args.inputdir
    threshold = args.threshold
    hash_size = args.hash_size
    bands = args.bands

    try:
        near_duplicates = find_near_duplicates(input_dir, threshold, hash_size, bands)
        groups = group_similar_images(near_duplicates)
        if near_duplicates:
           print(groups)
        else:
            print(f"No near-duplicates found in {input_dir} (threshold {threshold:.2%})")
    except OSError:
        print(f"Couldn't open input directory {input_dir}")
                    

if __name__ == "__main__":
    main(sys.argv)
