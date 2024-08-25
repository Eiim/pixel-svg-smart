import numpy as np
import imageio.v3 as iio
import copy

def convert_image_file(path: str):
    svg_data = convert_image_data(iio.imread(path, mode="RGBA"))
    with open(path + ".svg", "w") as f:
        f.write(svg_data)

def convert_image_data(data: np.ndarray) -> str:
    mask = [[c[3] > 0 for c in r] for r in data]
    unique_colors = set(tuple(c[:3]) for r in data for c in r if c[3] > 0)
    color_masks = {c: [[c == tuple(p[:3]) for p in r] for r in data] for c in unique_colors}
    ordered_colors = layering_random(mask, color_masks)
    paths = overlapping(mask, color_masks, ordered_colors)
    return f"<svg viewbox=\"0 0 {len(data[0])} {len(data)}\" width=\"{len(data[0])}\" height=\"{len(data)}\">" + "".join(paths) + "</svg>"

def layering_random(mask: list[list[bool]], color_masks: dict[tuple[np.uint8, np.uint8, np.uint8], list[list[bool]]]) -> list[tuple[np.uint8, np.uint8, np.uint8]]:
    return list(color_masks.keys())

def overlapping(mask: list[list[bool]], color_masks: dict[tuple[np.uint8, np.uint8, np.uint8], list[list[bool]]], ordered_colors: list[tuple[np.uint8, np.uint8, np.uint8]]) -> list[str]:
    paths = []
    for c in ordered_colors:
        print(f"Color: {c}")
        color_mask = color_masks[c]
        
        # Calculate contigous regions
        regions = []
        unused_mask = copy.deepcopy(color_mask)
        pixel_queue = []
        for i in range(len(unused_mask)):
            for j in range(len(unused_mask[i])):
                region = []
                if unused_mask[i][j]:
                    pixel_queue.append((i, j))
                    unused_mask[i][j] = False
                while pixel_queue:
                    x, y = pixel_queue.pop(0)
                    region.append((x, y))
                    if x+1 < len(unused_mask) and unused_mask[x+1][y]:
                        pixel_queue.append((x+1, y))
                        unused_mask[x+1][y] = False
                    if y+1 < len(unused_mask[x]) and unused_mask[x][y+1]:
                        pixel_queue.append((x, y+1))
                        unused_mask[x][y+1] = False
                    if x-1 >= 0 and unused_mask[x-1][y]:
                        pixel_queue.append((x-1, y))
                        unused_mask[x-1][y] = False
                    if y-1 >= 0 and unused_mask[x][y-1]:
                        pixel_queue.append((x, y-1))
                        unused_mask[x][y-1] = False
                if len(region) > 0:
                    regions.append(region)
        
        combined_d = ""
        for region in regions:
            print(f"Region: {region}")
            # Calculate region edges
            edges = []
            edges_are_outside = [[False]*(len(mask[0]) + r%2) for r in range(2*len(mask)+1)]
            for x, y in region:
                if x-1 < 0 or not color_mask[x-1][y]:
                    edges.append((x, y, x, y+1))
                    edges_are_outside[x*2][y] = x-1 < 0 or not mask[x-1][y]
                if y-1 < 0 or not color_mask[x][y-1]:
                    edges.append((x, y, x+1, y))
                    edges_are_outside[2*x+1][y] = y-1 < 0 or not mask[x][y-1]
                if x+1 >= len(color_mask) or not color_mask[x+1][y]:
                    edges.append((x+1, y, x+1, y+1))
                    edges_are_outside[(x+1)*2][y] = x+1 >= len(mask) or not mask[x+1][y]
                if y+1 >= len(color_mask[x]) or not color_mask[x][y+1]:
                    edges.append((x, y+1, x+1, y+1))
                    edges_are_outside[2*x+1][y+1] = y+1 >= len(mask[x]) or not mask[x][y+1]
            # Combine into outlines
            outlines = []
            print(f"Edges: {edges}")
            while edges:
                outline = []
                x, y, x2, y2 = edges.pop(0)
                outline.append((x, y))
                outline.append((x2, y2))
                while outline[0] != outline[-1]:
                    broken = False
                    for i in range(len(edges)):
                        ex, ey, ex2, ey2 = edges[i]
                        if (ex, ey) == outline[-1]:
                            outline.append((ex2, ey2))
                            broken = True
                            edges.pop(i)
                            break
                        if (ex2, ey2) == outline[-1]:
                            outline.append((ex, ey))
                            broken = True
                            edges.pop(i)
                            break
                    if not broken:
                        print(outline)
                        print(edges)
                        raise Exception("Outline failed to complete")
                outlines.append(outline)
            # (Temporary) generate path
            for outline in outlines:
                combined_d += generate_d([(y,x) for (x, y) in outline]) # Coordinates are actually reversed in-memory, flip before path creation
        
        paths.append(f'<path d="{combined_d}" fill="#{c[0]:02x}{c[1]:02x}{c[2]:02x}"/>')

    return paths

def generate_d(points: tuple[np.uint8, np.uint8]) -> str:
    start = points.pop(0)
    d = f"M{start[0]},{start[1]}"
    prev = start
    queued_direction = None
    queued_distance = 0
    while points:
        if(len(points) == 1):
            if(queued_direction == "h"):
                # Append horizontal line
                if(len(str(queued_distance)) < len(str(prev[0]))):
                    d += f"h{queued_distance}"
                else:
                    d += f"H{prev[0]}"
            elif(queued_direction == "v"):
                # Append vertical line
                if(len(str(queued_distance)) < len(str(prev[1]))):
                    d += f"v{queued_distance}"
                else:
                    d += f"V{prev[1]}"
            d += "Z"
            break
        point = points.pop(0)
        if(prev[0] == point[0]):
            if(queued_direction == "h"):
                # Append horizontal line
                if(len(str(queued_distance)) < len(str(point[0]))):
                    d += f"h{queued_distance}"
                else:
                    d += f"H{point[0]}"
                queued_distance = 0

            queued_direction = "v"
            queued_distance += point[1]-prev[1]
        elif(prev[1] == point[1]):
            if(queued_direction == "v"):
                # Append vertical line
                if(len(str(queued_distance)) < len(str(point[1]))):
                    d += f"v{queued_distance}"
                else:
                    d += f"V{point[1]}"
                queued_distance = 0
                
            queued_direction = "h"
            queued_distance += point[0]-prev[0]
        else: # How did we get here?
            if(queued_direction == "h"):
                # Append horizontal line
                if(len(str(queued_distance)) < len(str(prev[0]))):
                    d += f"h{queued_distance}"
                else:
                    d += f"H{prev[0]}"
            elif(queued_direction == "v"):
                # Append vertical line
                if(len(str(queued_distance)) < len(str(prev[1]))):
                    d += f"v{queued_distance}"
                else:
                    d += f"V{prev[1]}"
            queued_direction = None
            queued_distance = 0
            d += f"L{point[0]},{point[1]}"
        prev = point
    return d