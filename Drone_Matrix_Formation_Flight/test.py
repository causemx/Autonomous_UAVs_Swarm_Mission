from formation_function import (
    new_gps_coord_after_offset_inBodyFrame,
    distance_between_two_gps_coord,
)

# Generate a point, leader will fly to this point.
pointA = new_gps_coord_after_offset_inBodyFrame(
    (24.7734228, 121.0431711),
    100,
    0, #leader_heading
    0,
)

distance = distance_between_two_gps_coord(
        (24.7734228, 121.0431711),
        (pointA[0], pointA[1]),
)

print(f"pointA: {pointA}")
print(f"distance: {distance}")

  