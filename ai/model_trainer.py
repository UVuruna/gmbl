# ai/model_trainer.py
# Refactored from train_model_v4.py

import numpy as np
import pickle
import sqlite3
import json
from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from skimage.color import rgb2lab, lab2rgb
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from logger import AviatorLogger


class GMMWrapper:
    """Wrapper for GMM to match KMeans interface"""
    def __init__(self, gmm, labels):
        self.gmm = gmm
        self.labels_ = labels
        self.cluster_centers_ = gmm.means_
        self.n_clusters = gmm.n_components


class ModelTrainer:
    """Train clustering models for game phase detection"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.data = None
        self.lab_data = None
        self.model = None
        self.centers = {}
        self.logger = AviatorLogger.get_logger("ModelTrainer")
    
    def load_data(self, skip_first: int = 0):
        """Load RGB data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if skip_first > 0:
            cursor.execute(f"SELECT r, g, b FROM colors LIMIT -1 OFFSET {skip_first}")
            self.logger.info(f"Skipped first {skip_first:,} records")
        else:
            cursor.execute("SELECT r, g, b FROM colors")
        
        self.data = np.array(cursor.fetchall(), dtype=float)
        conn.close()
        
        self.logger.info(f"Loaded {len(self.data):,} records")
        return self.data
    
    def rgb_to_lab(self):
        """Convert RGB to LAB color space"""
        data_norm = self.data / 255.0
        self.lab_data = rgb2lab(data_norm.reshape(-1, 1, 3)).reshape(-1, 3)
        self.logger.info("Converted RGB to LAB")
        return self.lab_data
    
    def lab_to_rgb(self, lab_data):
        """Convert LAB back to RGB"""
        rgb_norm = lab2rgb(lab_data.reshape(-1, 1, 3)).reshape(-1, 3)
        return (rgb_norm * 255).clip(0, 255).astype(int)
    
    def evaluate_clusters(self, n_range=(3, 11)):
        """Evaluate different numbers of clusters"""
        sample_size = min(10000, len(self.lab_data))
        idx = np.random.choice(len(self.lab_data), sample_size, replace=False)
        sample = self.lab_data[idx]
        
        self.logger.info(f"Evaluating clusters {n_range[0]}-{n_range[1]-1} on {sample_size:,} samples")
        
        metrics = {'silhouette': {}, 'calinski': {}, 'davies_bouldin': {}}
        
        for n in range(n_range[0], n_range[1]):
            kmeans = KMeans(n_clusters=n, random_state=42, n_init=10).fit(sample)
            
            sil = silhouette_score(sample, kmeans.labels_)
            cal = calinski_harabasz_score(sample, kmeans.labels_)
            dav = davies_bouldin_score(sample, kmeans.labels_)
            
            metrics['silhouette'][n] = sil
            metrics['calinski'][n] = cal
            metrics['davies_bouldin'][n] = dav
            
            self.logger.info(f"n={n}: Silhouette={sil:.3f}, CH={cal:.1f}, DB={dav:.3f}")
        
        return metrics
    
    def train_kmeans(self, n_clusters: int = 6):
        """Train MiniBatch KMeans"""
        self.logger.info(f"Training MiniBatch KMeans with {n_clusters} clusters")
        
        self.model = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=42,
            batch_size=2000,
            n_init=20,
            max_iter=300,
            verbose=0
        ).fit(self.lab_data)
        
        self.logger.info("Training complete")
        self._extract_centers()
        return self.model
    
    def train_gmm(self, n_clusters: int = 6):
        """Train Gaussian Mixture Model"""
        self.logger.info(f"Training GMM with {n_clusters} components")
        
        gmm = GaussianMixture(
            n_components=n_clusters,
            covariance_type='full',
            random_state=42,
            n_init=10,
            max_iter=300,
            verbose=0
        ).fit(self.lab_data)
        
        labels = gmm.predict(self.lab_data)
        self.model = GMMWrapper(gmm, labels)
        
        self.logger.info("Training complete")
        self._extract_centers()
        return self.model
    
    def train_weighted_kmeans(self, n_clusters: int = 6):
        """Train weighted KMeans (emphasize small clusters)"""
        self.logger.info(f"Training Weighted KMeans with {n_clusters} clusters")
        
        # Initial model
        initial = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=42,
            batch_size=2000,
            n_init=10,
            max_iter=100
        ).fit(self.lab_data)
        
        # Find small clusters
        unique, counts = np.unique(initial.labels_, return_counts=True)
        small_clusters = unique[counts < len(self.lab_data) * 0.05]
        
        # Create weights
        weights = np.ones(len(self.lab_data))
        for cluster_id in small_clusters:
            mask = initial.labels_ == cluster_id
            weights[mask] = 3.0
        
        self.logger.info(f"Found {len(small_clusters)} small clusters, boosting their weight")
        
        # Retrain with weights
        self.model = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=42,
            batch_size=2000,
            n_init=20,
            max_iter=300,
            verbose=0
        ).fit(self.lab_data, sample_weight=weights)
        
        self.logger.info("Training complete")
        self._extract_centers()
        return self.model
    
    def _extract_centers(self):
        """Extract cluster centers"""
        centers_lab = self.model.cluster_centers_
        centers_rgb = self.lab_to_rgb(centers_lab)
        
        for i in range(self.model.n_clusters):
            mask = self.model.labels_ == i
            count = np.sum(mask)
            percentage = (count / len(self.data)) * 100
            
            self.centers[i] = {
                'rgb': centers_rgb[i].tolist(),
                'count': int(count),
                'percentage': round(percentage, 2)
            }
            
            self.logger.info(
                f"Cluster {i}: RGB{tuple(centers_rgb[i])} - "
                f"{count:,} points ({percentage:.2f}%)"
            )
    
    def save_model(self, model_path: str):
        """Save model to file"""
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        self.logger.info(f"Model saved: {model_path}")
    
    def save_mapping(self, mapping_path: str, model_name: str):
        """Save model mapping to JSON"""
        try:
            with open(mapping_path, 'r') as f:
                mappings = json.load(f)
        except:
            mappings = {}
        
        # Update version
        if model_name in mappings:
            old_version = float(mappings[model_name].get('version', '1.00'))
            new_version = f"{old_version + 0.01:.2f}"
        else:
            new_version = '1.00'
        
        # Create mapping
        mapping = {}
        for cluster_id, data in self.centers.items():
            mapping[str(cluster_id)] = {
                'RGB': data['rgb'],
                'percentage': data['percentage']
            }
        
        mapping['total data'] = len(self.data)
        mapping['version'] = new_version
        
        mappings[model_name] = mapping
        
        # Save
        with open(mapping_path, 'w') as f:
            json.dump(mappings, f, indent=4)
        
        self.logger.info(f"Mapping saved: {mapping_path}")
    
    def visualize_3d(self, labels=None, title="RGB Space", max_points=5000):
        """3D visualization"""
        if len(self.data) > max_points:
            idx = np.random.choice(len(self.data), max_points, replace=False)
            data_sample = self.data[idx]
            labels_sample = labels[idx] if labels is not None else None
        else:
            data_sample = self.data
            labels_sample = labels
        
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        if labels_sample is None:
            ax.scatter(data_sample[:, 0], data_sample[:, 1], data_sample[:, 2],
                      c=data_sample/255.0, s=1, alpha=0.6)
        else:
            scatter = ax.scatter(data_sample[:, 0], data_sample[:, 1], data_sample[:, 2],
                               c=labels_sample, cmap='tab10', s=3, alpha=0.7)
            plt.colorbar(scatter, label='Cluster ID')
        
        ax.set_xlabel('Red')
        ax.set_ylabel('Green')
        ax.set_zlabel('Blue')
        ax.set_title(f"{title}\n({len(data_sample):,} / {len(self.data):,} points)")
        plt.tight_layout()
        plt.show()


def main():
    from logger import init_logging
    
    init_logging()
    
    print("=" * 60)
    print("MODEL TRAINER - Game Phase Clustering")
    print("=" * 60)
    
    db_name = input("\nDatabase name (default 'game_phase'): ").strip() or "game_phase"
    db_path = f"db/{db_name}.db"
    
    skip = input("Skip first N records? (default 0): ").strip()
    skip_first = int(skip) if skip else 0
    
    print("\nAlgorithm:")
    print("1. KMeans (fast, balanced)")
    print("2. GMM (flexible)")
    print("3. Weighted KMeans (boost small clusters)")
    algo_choice = input("Choose (1-3, default 1): ").strip() or "1"
    
    n_clusters = int(input("Number of clusters (default 6): ").strip() or "6")
    
    # Train
    trainer = ModelTrainer(db_path)
    trainer.load_data(skip_first)
    trainer.rgb_to_lab()
    
    # Evaluate
    trainer.evaluate_clusters()
    
    # Train
    if algo_choice == '2':
        trainer.train_gmm(n_clusters)
        algo_name = 'gmm'
    elif algo_choice == '3':
        trainer.train_weighted_kmeans(n_clusters)
        algo_name = 'weighted'
    else:
        trainer.train_kmeans(n_clusters)
        algo_name = 'kmeans'
    
    # Save
    model_path = f"data/models/{db_name}_{algo_name}.pkl"
    trainer.save_model(model_path)
    trainer.save_mapping("data/models/model_mapping.json", f"{db_name}_{algo_name}.pkl")
    
    # Visualize
    print("\nVisualize? (y/n): ", end='')
    if input().strip().lower() == 'y':
        trainer.visualize_3d(trainer.model.labels_, f"{algo_name.upper()} Clusters")
    
    print("\nTraining complete!")


if __name__ == "__main__":
    main()
