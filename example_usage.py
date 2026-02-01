#!/usr/bin/env python3
"""
Quick example demonstrating basic DHT usage.
"""

from dht.chord import Chord
from dht.pastry import Pastry
from dht.data_loader import create_sample_dataset

def main():
    print("="*60)
    print("DHT Quick Example")
    print("="*60)

    # Create sample data
    print("\n1. Creating sample dataset (100 movies)...")
    movies = create_sample_dataset(100)
    print(f"   Created {len(movies)} movie records")

    # Test Chord
    print("\n2. Testing Chord DHT...")
    chord = Chord(m=8)  # Small identifier space for demo
    node_ids = [10, 50, 100, 150, 200]
    chord.build(node_ids, movies)
    print(f"   Built Chord with {len(chord.get_all_nodes())} nodes")

    # Perform lookup
    test_title = movies[0][0]
    values, hops = chord.lookup(test_title)
    print(f"   Lookup '{test_title}': Found {len(values) if values else 0} records, {hops} hops")

    # Insert new movie
    hops = chord.insert("new_movie_title", movies[0][1])
    print(f"   Insert: {hops} hops")

    # Test Pastry
    print("\n3. Testing Pastry DHT...")
    pastry = Pastry(m=8, b=2)
    pastry.build(node_ids, movies)
    print(f"   Built Pastry with {len(pastry.get_all_nodes())} nodes")

    # Perform lookup
    values, hops = pastry.lookup(test_title)
    print(f"   Lookup '{test_title}': Found {len(values) if values else 0} records, {hops} hops")

    # Insert new movie
    hops = pastry.insert("new_movie_title", movies[0][1])
    print(f"   Insert: {hops} hops")

    print("\n" + "="*60)
    print("Example completed successfully!")
    print("Try running: python main.py --test")
    print("="*60)

if __name__ == "__main__":
    main()
