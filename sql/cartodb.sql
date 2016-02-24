SELECT 
    SUM(
      ST_Length(
        ST_INTERSECTION(
            s.the_geom::geography,
            k.the_geom::geography
        )
      )
    ) / 1000 as len
from 
    kommuner k, skiloype s
WHERE 
    ST_Intersects(k.the_geom, s.the_geom)
AND K.komm = '1001'