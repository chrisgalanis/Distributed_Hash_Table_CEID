"""Data loading utilities for movies dataset."""

import csv
from typing import List, Tuple, Dict, Any, Optional
from dht.common import normalize_title


class Movie:
    """Movie data structure."""

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id', '')
        self.title = data.get('title', '')
        self.adult = data.get('adult', 'False') == 'True'
        self.original_language = data.get('original_language', '')
        self.origin_country = data.get('origin_country', '')
        self.release_date = data.get('release_date', '')
        self.genre_names = data.get('genre_names', '')
        self.production_company_names = data.get('production_company_names', '')

        # Convert numeric fields
        try:
            self.budget = float(data.get('budget', 0))
        except (ValueError, TypeError):
            self.budget = 0.0

        try:
            self.revenue = float(data.get('revenue', 0))
        except (ValueError, TypeError):
            self.revenue = 0.0

        try:
            self.runtime = float(data.get('runtime', 0))
        except (ValueError, TypeError):
            self.runtime = 0.0

        try:
            self.popularity = float(data.get('popularity', 0))
        except (ValueError, TypeError):
            self.popularity = 0.0

        try:
            self.vote_average = float(data.get('vote_average', 0))
        except (ValueError, TypeError):
            self.vote_average = 0.0

        try:
            self.vote_count = int(data.get('vote_count', 0))
        except (ValueError, TypeError):
            self.vote_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert movie to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'adult': self.adult,
            'original_language': self.original_language,
            'origin_country': self.origin_country,
            'release_date': self.release_date,
            'genre_names': self.genre_names,
            'production_company_names': self.production_company_names,
            'budget': self.budget,
            'revenue': self.revenue,
            'runtime': self.runtime,
            'popularity': self.popularity,
            'vote_average': self.vote_average,
            'vote_count': self.vote_count
        }

    def __repr__(self):
        return f"Movie(title='{self.title}', popularity={self.popularity}, release_date='{self.release_date}')"


def load_movies(file_path: str, max_records: Optional[int] = None) -> List[Tuple[str, Movie]]:
    """
    Load movies from CSV file.
    Returns list of (normalized_title, Movie) tuples.

    Args:
        file_path: Path to CSV file
        max_records: Maximum number of records to load (None for all)
    """
    movies = []
    seen_titles = set()  # Track unique movie titles

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Try comma delimiter first
            first_line = f.readline()
            f.seek(0)

            delimiter = ',' if ',' in first_line else ';'
            reader = csv.DictReader(f, delimiter=delimiter)

            for i, row in enumerate(reader):
                if max_records and len(movies) >= max_records:
                    break

                # Check for different possible title column names
                title = row.get('title') or row.get('Movie_Name') or row.get('movie_name')
                if not title:
                    continue

                # Skip duplicates (same movie can have multiple ratings)
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # Create Movie object with available data
                movie_data = {
                    'id': row.get('id', str(i)),
                    'title': title,
                    'genre_names': row.get('genre_names') or row.get('Genre', ''),
                    'popularity': float(row.get('popularity') or row.get('Rating', '5.0')),
                }

                movie = Movie(movie_data)
                normalized_title = normalize_title(movie.title)

                movies.append((normalized_title, movie))

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading movies: {e}")
        return []

    return movies


def create_sample_dataset(num_movies: int = 1000) -> List[Tuple[str, Movie]]:
    """
    Create a sample dataset for testing without CSV file.
    Generates synthetic movie data.
    """
    import random

    movies = []
    genres = ['Action', 'Comedy', 'Drama', 'Horror', 'Sci-Fi', 'Romance', 'Thriller']
    languages = ['en', 'es', 'fr', 'de', 'ja', 'ko']

    for i in range(num_movies):
        title = f"Movie {i}"
        data = {
            'id': str(i),
            'title': title,
            'adult': random.choice(['True', 'False']),
            'original_language': random.choice(languages),
            'origin_country': random.choice(['US', 'UK', 'FR', 'DE', 'JP']),
            'release_date': f"{random.randint(1990, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            'genre_names': random.choice(genres),
            'production_company_names': f"Studio {random.randint(1, 10)}",
            'budget': str(random.randint(1000000, 200000000)),
            'revenue': str(random.randint(5000000, 1000000000)),
            'runtime': str(random.randint(80, 180)),
            'popularity': str(random.uniform(1, 100)),
            'vote_average': str(random.uniform(1, 10)),
            'vote_count': str(random.randint(100, 50000))
        }

        movie = Movie(data)
        normalized_title = normalize_title(title)
        movies.append((normalized_title, movie))

    return movies


def get_popular_movie_titles(movies: List[Tuple[str, Movie]], k: int = 10) -> List[str]:
    """
    Get K most popular movie titles from dataset.

    Args:
        movies: List of (title, Movie) tuples
        k: Number of titles to return

    Returns:
        List of normalized titles
    """
    # Sort by popularity
    sorted_movies = sorted(movies, key=lambda x: x[1].popularity, reverse=True)

    # Get top K titles
    return [title for title, _ in sorted_movies[:k]]


def lookup_popularity_concurrent(dht, titles: List[str]) -> Dict[str, float]:
    """
    Lookup popularity of K movies concurrently.

    Args:
        dht: DHT instance (Chord or Pastry)
        titles: List of movie titles to lookup

    Returns:
        Dictionary mapping title to popularity (or 0 if not found)
    """
    import concurrent.futures

    results = {}

    def lookup_single(title: str) -> Tuple[str, float, int]:
        """Lookup single title and return (title, popularity, hops)."""
        values, hops = dht.lookup(title)
        if values:
            # Get max popularity if multiple records
            max_pop = max(movie.popularity for movie in values)
            return title, max_pop, hops
        return title, 0.0, hops

    # Use thread pool for concurrent lookups
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(titles), 10)) as executor:
        futures = [executor.submit(lookup_single, title) for title in titles]

        total_hops = 0
        for future in concurrent.futures.as_completed(futures):
            title, popularity, hops = future.result()
            results[title] = popularity
            total_hops += hops

    return results, total_hops
