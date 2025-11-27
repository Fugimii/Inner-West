import polars as pl

class BradleyTerryModel:
    def __init__(self, matches: pl.DataFrame):
        """
        matches must have two columns: 'winner' and 'loser'
        """
        self.df = matches
        competitors = set(matches["winner"].to_list()) | set(matches["loser"].to_list())
        self.strengths = {c: 1.0 for c in competitors}

    def probability(self, i, j):
        return self.strengths[i] / (self.strengths[i] + self.strengths[j])

    def fit(self, max_iter=100, tol=1e-6):
        for _ in range(max_iter):
            new_strengths = {}
            converged = True
            for i in self.strengths:
                wins = self.df.filter(pl.col("winner") == i).height
                expected = 0.0
                for row in self.df.iter_rows(named=True):
                    if row["winner"] == i or row["loser"] == i:
                        opponent = row["loser"] if row["winner"] == i else row["winner"]
                        expected += self.probability(i, opponent)
                new_strengths[i] = wins / expected if expected > 0 else self.strengths[i]
                if abs(new_strengths[i] - self.strengths[i]) > tol:
                    converged = False
            self.strengths = new_strengths
            if converged:
                break

    def get_strengths(self):
        return pl.DataFrame({
            "suburb": list(self.strengths.keys()),
            "strength": list(self.strengths.values())
        }).sort("strength", descending=True)
