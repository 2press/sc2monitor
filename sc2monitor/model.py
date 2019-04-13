"""Define model (database structure) of sc2monitor."""
import enum
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Enum, Float, ForeignKey,
                        Integer, String, UniqueConstraint, create_engine, text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Result(enum.Enum):
    """Result of a ladder match."""

    Unknown = 0
    Win = 1
    Loss = 2
    Tie = 3

    @classmethod
    def get(cls, value):
        """Get a Result based on input value."""
        if isinstance(value, Result):
            return value
        elif isinstance(value, str):
            if not value:
                return cls.Unknown
            for result in cls.__members__:
                if result[0].lower() == value[0].lower():
                    return cls[result]
        elif isinstance(value, int):
            if value >= 1:
                return cls.Win
            elif value <= -1:
                return cls.Loss
            elif value == 0:
                return cls.Tie

        return cls.Unknown

    def change(self):
        """Get sign of the result."""
        if self.value == 1:
            return 1.0
        elif self.value == 2:
            return -1.0
        else:
            return 0.0

    def describe(self):
        """Return description of the result."""
        if self.value == 1:
            desc = "Win"
        elif self.value == 2:
            desc = "Loss"
        elif self.value == 3:
            desc = "Tie"
        else:
            desc = "Unknown"

        return desc

    def short(self):
        """Return short description of the result."""
        if self.value == 1:
            desc = "W"
        elif self.value == 2:
            desc = "L"
        elif self.value == 3:
            desc = "D"
        else:
            desc = "U"

        return desc

    def __str__(self):
        """Represent result as string."""
        return self.describe()


class Race(enum.Enum):
    """StarCraft 2 race."""

    Random = 0
    Protoss = 1
    Terran = 2
    Zerg = 3

    @classmethod
    def get(cls, value):
        """Return a SC2 race based on input value."""
        if isinstance(value, Race):
            return value
        elif isinstance(value, str):
            if not value:
                return cls.Random
            for race in cls.__members__:
                if race[0].lower() == value[0].lower():
                    return cls[race]
        raise ValueError(f'Unknown race {value}')

    def describe(self):
        """Return the name of race."""
        if self.value == 1:
            desc = "Protoss"
        elif self.value == 2:
            desc = "Terran"
        elif self.value == 3:
            desc = "Zerg"
        else:
            desc = "Random"

        return desc

    def short(self):
        """Return first letter of race."""
        if self.value == 1:
            desc = "P"
        elif self.value == 2:
            desc = "T"
        elif self.value == 3:
            desc = "Z"
        else:
            desc = "R"

        return desc

    def __str__(self):
        """Return the name of race."""
        return self.describe()


class Server(enum.Enum):
    """StarCraft 2 Server."""

    Unknown = 0
    America = 1
    Europe = 2
    Korea = 3

    def describe(self):
        """Return the name of the server."""
        if self.value == 1:
            desc = "America"
        elif self.value == 2:
            desc = "Europe"
        elif self.value == 3:
            desc = "Korea"

        return desc

    def short(self):
        """Return the short name of the server."""
        if self.value == 1:
            desc = "us"
        elif self.value == 2:
            desc = "eu"
        elif self.value == 3:
            desc = "kr"

        return desc

    def id(self):
        """Return the id of the server used by the api."""
        return self.value

    def __str__(self):
        """Return the name of the server."""
        return self.describe()


class League(enum.Enum):
    """StarCraft 2 League."""

    Unranked = -1
    Bronze = 0
    Silver = 1
    Gold = 2
    Platinum = 3
    Diamond = 4
    Master = 5
    Grandmaster = 6

    def __ge__(self, other):
        """Test if a league is higher or equal to another."""
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        """Test if a league is higher to another."""
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        """Test if a league is lower or equal to another."""
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        """Test if a league is lower to another."""
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    @classmethod
    def get(cls, value):
        """Return league based on input value."""
        if isinstance(value, League):
            return value
        elif isinstance(value, str):
            if not value:
                return cls.Unranked
            if value[0:2].lower() == 'gm':
                return League.Grandmaster
            for league in cls.__members__:
                if league[0:2].lower() == value[0:2].lower():
                    return cls[league]
            for league in cls.__members__:
                if league[0].lower() == value[0].lower():
                    return cls[league]
        elif isinstance(value, int):
            return League(value)
        raise ValueError(f'Unknown league {value}')

    def describe(self):
        """Return the name of the league."""
        if self.value == 0:
            desc = "Bronze"
        elif self.value == 1:
            desc = "Silver"
        elif self.value == 2:
            desc = "Gold"
        elif self.value == 3:
            desc = "Platinum"
        elif self.value == 4:
            desc = "Diamond"
        elif self.value == 5:
            desc = "Master"
        elif self.value == 6:
            desc = "Grandmaster"
        else:
            desc = "Unranked"

        return desc

    def id(self):
        """Return the id of the league used by the api."""
        return self.value

    def __str__(self):
        """Return the name of the league."""
        return self.describe()


def same_as(column_name):
    """Provide SQLAlchemy with a default value based on another column."""
    def default_function(context):
        return context.current_parameters.get(column_name)
    return default_function


class Config(Base):
    """Config database entry."""

    __tablename__ = "config"
    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True)
    value = Column(String(128))

    def __repr__(self):
        """Represent database object."""
        return f'<Config(id={self.id}, key={self.key}, value={self.value})>'


class Season(Base):
    """Season database entry."""

    __tablename__ = "season"
    id = Column(Integer, primary_key=True)
    season_id = Column(Integer)
    server = Column(Enum(Server), default=Server.Europe)
    year = Column(Integer)
    number = Column(Integer)
    start = Column(DateTime)
    end = Column(DateTime)

    def __repr__(self):
        """Represent database object."""
        return (f'<Season(id={self.id}, season_id={self.season_id}, '
                f'server={self.server}, year={self.year}, '
                f'number={self.number}, start={self.start}, end={self.end})>')


class Player(Base):
    """Player database entry."""

    __tablename__ = "player"
    __table_args__ = tuple(UniqueConstraint(
        'player_id', 'realm', 'server', 'race'))
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer)
    realm = Column(Integer, default=1, server_default=text("1"))
    server = Column(Enum(Server), default=Server.Europe)
    name = Column(String(64), default='')
    race = Column(Enum(Race), default=Race.Random)
    ladder_id = Column(Integer, default=0, server_default=text("0"))
    league = Column(Enum(League), default=League.Unranked)
    mmr = Column(Integer, default=0, server_default=text("0"))
    wins = Column(Integer, default=0, server_default=text("0"))
    losses = Column(Integer, default=0, server_default=text("0"))
    refreshed = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_played = Column(DateTime)
    ladder_joined = Column(DateTime)
    last_active_season = Column(Integer, default=0)
    matches = relationship("Match",
                           back_populates="player",
                           order_by="desc(Match.datetime)",
                           cascade="save-update, merge, delete")
    statistics = relationship("Statistics",
                              back_populates="player",
                              uselist=False,
                              cascade="save-update, merge, delete")

    def __repr__(self):
        """Represent database object."""
        return (f'<Player(id={self.id}, player_id={self.player_id}, '
                f'server={self.server}, realm={self.realm}, '
                f'ladder={self.ladder_id}, name={self.name}, '
                f'race={self.race}, mmr={self.mmr}, wins={self.wins}, '
                f'losses={self.losses})>')


class Match(Base):
    """Match database entry."""

    __tablename__ = "match"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player, back_populates="matches", uselist=False)
    result = Column(Enum(Result), default=Result.Unknown)
    datetime = Column(DateTime, default=datetime.now)
    mmr = Column(Integer, default=0, server_default=text("0"))
    mmr_change = Column(Integer, default=0, server_default=text("0"))
    guess = Column(Boolean, default=False, server_default=text("0"))
    max_length = Column(Integer, default=180, server_default=text("180"))
    ema_mmr = Column(Float, default=same_as('mmr'))
    emvar_mmr = Column(Float, default=0.0, server_default=text("0.0"))

    def __repr__(self):
        """Represent database object."""
        return (f'<Match(id={self.id}, player={self.player}, '
                f'result={self.result}, datetime={self.datetime}, '
                f'mmr={self.mmr}, mmr_change={self.mmmr_change}, '
                f'guess={self.guess})>')


class Statistics(Base):
    """Statistics database entry."""

    __tablename__ = "statistics"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'))
    player = relationship(Player, back_populates="statistics", uselist=False)
    winrate = Column(Float, default=0.0)
    games = Column(Integer, default=0)
    current_mmr = Column(Integer, default=0)
    wma_mmr = Column(Integer, default=0)
    max_mmr = Column(Integer, default=0)
    min_mmr = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    longest_wining_streak = Column(Integer, default=0)
    longest_losing_streak = Column(Integer, default=0)
    guessed_games = Column(Integer, default=0)
    lr_mmr_slope = Column(Float, default=0.0)
    lr_mmr_intercept = Column(Float, default=0.0)
    sd_mmr = Column(Float, default=0.0)
    avg_mmr = Column(Float, default=0.0)
    instant_left_games = Column(Integer, default=0)

    def __repr__(self):
        """Represent database object."""
        return (f'<Statistics(id={self.id}, player={self.player}, '
                f'games={self.games})>')


class Log(Base):
    """Log database entry."""

    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)  # auto incrementing
    logger = Column(String(64))  # the name of the logger. (e.g. myapp.views)
    level = Column(String(64))  # info, debug, or error?
    trace = Column(String(2048))  # the full traceback printout
    msg = Column(String(255))  # any custom log you may have included
    datetime = Column(DateTime, default=datetime.now)

    def __init__(self, logger=None, level=None, trace=None, msg=None):
        """Init object."""
        self.logger = logger
        self.level = level
        self.trace = trace
        self.msg = msg

    def __unicode__(self):
        """Translate to unicode."""
        return self.__repr__()

    def __repr__(self):
        """Represent database object."""
        return "<Log: {} - {}>".format(
            self.datetime.strftime('%m/%d/%Y-%H:%M:%S'), self.msg[:100])


class Run(Base):
    """Run database entry."""

    __tablename__ = "runs"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, default=datetime.now)
    duration = Column(Float, default=0.0)
    api_requests = Column(Integer, default=0)
    api_retries = Column(Integer, default=0)
    warnings = Column(Integer, default=0)
    errors = Column(Integer, default=0)

    def __repr__(self):
        """Represent database object."""
        return (f'<Run(id={self.id}, datetime={self.datetime}, '
                f'duration={self.duration:.2f}, '
                f'api_requests={self.api_requests}), '
                f'api_retries={self.api_retries}, warnings={self.warnings}, '
                f'errors={self.errors}>')


def create_db_session(db='', encoding=''):
    """Create a new database session."""
    if not db:
        db = 'sqlite:///sc2monitor.db'
    if not encoding:
        encoding = 'utf8'
    engine = create_engine(db, encoding=encoding)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    return sessionmaker(bind=engine)()
