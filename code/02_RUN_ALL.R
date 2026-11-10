# =====================================================================================
# 02_RUN_ALL.R — 한국 인앱결제 LTA: R 단일 파일 실행본
# -------------------------------------------------------------------------------------
# 하는 일   : 노트북(01_Korea_InApp_LTA_analysis.ipynb)의 B부(잠재전이분석)를 R 로 독립 구현해 재현한다.
#             ① 자료 읽기 → ② 상태 수 선택(K=1~4) → ③ 측정불변성·전이 동질성 검정
#             → ④ 부트스트랩 구간 → ⑤ 그림 4장 → ⑥ 파이썬·LMest 와의 교차검증 표
# 실행 방법 : RStudio 에서 이 파일을 열고 Source(또는 Ctrl+Shift+Enter). 파일 하나로 끝까지 돈다.
#             명령행: Rscript 02_RUN_ALL.R
# 필요 패키지: ggplot2 (그림). LMest 는 있으면 교차검증에 쓰고 없으면 건너뛴다.
# 자료      : data/synthetic_panel_long.csv (노트북이 만든 모의패널).
#             실제 원자료를 쓰려면 data/private/consumer_panel.csv 를 같은 열 구성
#             (id, wave, paid_app, inapp_item, paid_video, paid_music; 값은 0/1/빈칸)으로 두고
#             아래 DATA_MODE 를 'real' 로 바꾼다.
# 주의      : 모의패널 결과는 분석 절차의 검증용이며 한국 규제의 효과 추정치가 아니다.
# =====================================================================================

if (.Platform$OS.type == 'windows') invisible(suppressWarnings(Sys.setlocale('LC_CTYPE', 'English_United States.utf8')))

# ── 0. 설정 ───────────────────────────────────────────────────────────────────────────
DATA_MODE <- 'synthetic'                      # 'synthetic' 또는 'real'
ITEMS     <- c('paid_app', 'inapp_item', 'paid_video', 'paid_music')   # 이진 지표 4개
WAVES     <- 2020:2024                        # 분석 시점
K_GRID    <- 1:4                              # 비교할 상태 수
N_START   <- as.integer(Sys.getenv('LTA_NSTART', '3'))   # 모형별 무작위 초기값 수
MAXIT_SEL <- 1000                             # 상태 수 선택 단계의 EM 최대 반복(과적합 모형은 수렴이 느리다)
N_BOOT    <- as.integer(Sys.getenv('LTA_BOOT', '200'))   # 부트스트랩 반복 수(환경변수로 변경 가능)
SEED      <- 1104
REGIMES   <- c(0, 0, 1, 1)                    # 두 국면: 2020→21·21→22 / 22→23·23→24

# 프로젝트 폴더 찾기: 이 파일이 있는 code/ 의 부모 폴더(data/ 가 있는 곳)
.find_root <- function() {
  cand <- c(sub('^--file=', '', grep('^--file=', commandArgs(FALSE), value = TRUE)),
            tryCatch(sys.frame(1)$ofile, error = function(e) NULL),
            if (requireNamespace('rstudioapi', quietly = TRUE) && rstudioapi::isAvailable())
              tryCatch(rstudioapi::getSourceEditorContext()$path, error = function(e) NULL))
  dirs <- unique(c(dirname(normalizePath(cand[nzchar(cand)], mustWork = FALSE)), getwd()))
  for (d in dirs) for (r in c(d, dirname(d))) if (dir.exists(file.path(r, 'data'))) return(r)
  stop('data/ 폴더를 찾지 못했습니다. 코드집 폴더 전체를 유지한 채 실행하세요.')
}
ROOT <- .find_root()
OUT  <- file.path(ROOT, 'outputs'); FIG <- file.path(ROOT, 'figures')
dir.create(OUT, showWarnings = FALSE); dir.create(FIG, showWarnings = FALSE)
cat('ROOT =', ROOT, '\n')

# ── 1. 자료 읽기: long 형식 → (개체 N) × (시점 T) × (문항 J) 배열 ─────────────────────
panel_file <- if (DATA_MODE == 'real') file.path(ROOT, 'data/private/consumer_panel.csv') else
  file.path(ROOT, 'data/synthetic_panel_long.csv')
if (!file.exists(panel_file)) stop('자료 파일이 없습니다: ', panel_file, '\n모의패널은 노트북을 먼저 실행하면 만들어집니다.')
panel <- read.csv(panel_file, colClasses = c(id = 'character'))      # ID 는 문자형(앞자리 0 보존)
stopifnot(!any(duplicated(panel[, c('id', 'wave')])))                # 같은 개인·연도 중복 금지
stopifnot(all(is.na(unlist(panel[ITEMS])) | unlist(panel[ITEMS]) %in% c(0, 1)))   # 0/1/결측만 허용
ids <- sort(unique(panel$id)); N <- length(ids); TT <- length(WAVES); J <- length(ITEMS)
Y <- array(NA_real_, c(N, TT, J))                                    # 조사 미참여 시점은 NA 로 남는다
ii <- match(panel$id, ids); tt <- match(panel$wave, WAVES); ok <- !is.na(tt)
for (j in seq_len(J)) Y[cbind(ii[ok], tt[ok], j)] <- panel[[ITEMS[j]]][ok]
cat(sprintf('개체 %d명 × 시점 %d개 × 문항 %d개\n', N, TT, J))

# ── 2. LTA 엔진 ───────────────────────────────────────────────────────────────────────
# 모형: 첫 시점 상태확률 pi[k], 구간별 전이확률 A[t,a,b], 응답확률 theta[t,j,k].
# 결측 응답은 0 으로 바꾸지 않고 우도에서 주변화한다(MAR 가정).
CLIP <- 1e-8
mat  <- function(x, r, c) matrix(x, r, c)                            # 차원이 1일 때도 행렬 모양 유지

# E-step: scaled forward-backward. YM = 관측된 1, NM = 관측된 0, w = 개체(패턴) 가중치
lta_estep <- function(YM, NM, pi, A, theta, w) {
  N <- dim(YM)[1]; TT <- dim(YM)[2]; J <- dim(YM)[3]; K <- length(pi)
  B <- alpha <- beta <- array(1, c(N, TT, K)); cc <- matrix(0, N, TT)
  for (t in seq_len(TT)) {                                           # 방출확률 B[n,t,k] = Π_j θ^y (1-θ)^(1-y)
    th <- mat(theta[t, , ], J, K)
    B[, t, ] <- exp(mat(YM[, t, ], N, J) %*% log(th) + mat(NM[, t, ], N, J) %*% log1p(-th))
  }
  a <- sweep(mat(B[, 1, ], N, K), 2, pi, `*`); cc[, 1] <- rowSums(a); alpha[, 1, ] <- a / cc[, 1]
  for (t in 2:TT) {                                                  # 전방 재귀(시점마다 정규화)
    a <- (mat(alpha[, t - 1, ], N, K) %*% mat(A[t - 1, , ], K, K)) * mat(B[, t, ], N, K)
    cc[, t] <- rowSums(a); alpha[, t, ] <- a / cc[, t]
  }
  xi <- array(0, c(TT - 1, K, K))
  for (t in (TT - 1):1) {                                            # 후방 재귀 + 전이 기대빈도
    right <- mat(B[, t + 1, ], N, K) * mat(beta[, t + 1, ], N, K) / cc[, t + 1]
    beta[, t, ] <- right %*% t(mat(A[t, , ], K, K))
    xi[t, , ] <- (t(mat(alpha[, t, ], N, K) * w) %*% right) * mat(A[t, , ], K, K)
  }
  gamma <- alpha * beta; gamma <- gamma / as.vector(rowSums(gamma, dims = 2))   # 상태 사후확률
  list(gamma = gamma, xi = xi, loglik = sum(w * rowSums(log(cc))))
}

# 전이행렬 묶음: 동질(모두 같은 행렬), 국면(사용자 지정), 이질(구간마다 다름)
lta_groups <- function(TT, homog = FALSE, a_groups = NULL)
  if (!is.null(a_groups)) a_groups else if (homog) rep(0, TT - 1) else seq_len(TT - 1)

# 초기값 하나로 EM 실행
lta_fit_once <- function(Y, K, invariant = TRUE, homog = FALSE, a_groups = NULL, w = NULL,
                         maxit = 3000, tol = 1e-9, seed = 1, init = NULL) {
  if (is.null(init)) set.seed(seed)                                  # 무작위 초기값을 쓸 때만 난수 고정(부트스트랩 난수열을 건드리지 않음)
  N <- dim(Y)[1]; TT <- dim(Y)[2]; J <- dim(Y)[3]
  M <- array(as.numeric(!is.na(Y)), dim(Y)); YM <- Y; YM[is.na(Y)] <- 0; NM <- M - YM
  YM2 <- mat(YM, N * TT, J); M2 <- mat(M, N * TT, J)
  if (is.null(w)) w <- rep(1, N); groups <- lta_groups(TT, homog, a_groups)
  if (is.null(init)) {                                               # 무작위 초기값
    pi <- rep(1 / K, K); A <- array(0, c(TT - 1, K, K))
    for (t in seq_len(TT - 1)) { m <- mat(runif(K * K, .3, 1), K, K) + diag(K); A[t, , ] <- m / rowSums(m) }
    th <- mat(runif(J * K, .08, .92), J, K); theta <- array(0, c(TT, J, K)); for (t in seq_len(TT)) theta[t, , ] <- th
  } else { pi <- init$pi; A <- init$A; theta <- init$theta }
  trace <- numeric(); converged <- FALSE
  for (iter in seq_len(maxit)) {
    e <- lta_estep(YM, NM, pi, A, theta, w); trace <- c(trace, e$loglik)
    if (iter > 1 && abs(trace[iter] - trace[iter - 1]) < tol * (1 + abs(trace[iter]))) { converged <- TRUE; break }
    if (iter == maxit) break
    g <- e$gamma * w                                                 # 가중 사후확률
    pi <- colSums(mat(g[, 1, ], N, K)) / sum(w)                      # M-step: 초기확률
    for (gid in unique(groups)) {                                    # M-step: 전이확률(같은 묶음은 합산)
      idx <- which(groups == gid); cnt <- mat(0, K, K)
      for (t in idx) cnt <- cnt + mat(e$xi[t, , ], K, K)
      rs <- rowSums(cnt); new <- cnt / ifelse(rs > 1e-12, rs, 1)
      for (t in idx) { old <- mat(A[t, , ], K, K); new[rs <= 1e-12, ] <- old[rs <= 1e-12, ]; A[t, , ] <- new }
    }
    if (invariant) {                                                 # M-step: 응답확률(시점 간 동일)
      g2 <- mat(g, N * TT, K); th <- (t(YM2) %*% g2) / pmax(t(M2) %*% g2, 1e-300)
      th <- pmin(pmax(th, CLIP), 1 - CLIP); for (t in seq_len(TT)) theta[t, , ] <- th
    } else for (t in seq_len(TT)) {                                  # M-step: 응답확률(시점별 자유)
      gt <- mat(g[, t, ], N, K); th <- (t(mat(YM[, t, ], N, J)) %*% gt) / pmax(t(mat(M[, t, ], N, J)) %*% gt, 1e-300)
      theta[t, , ] <- pmin(pmax(th, CLIP), 1 - CLIP)
    }
  }
  npar <- (K - 1) + length(unique(groups)) * K * (K - 1) + J * K * (if (invariant) 1 else TT)
  list(K = K, pi = pi, A = A, theta = theta, loglik = e$loglik, npar = npar,
       aic = -2 * e$loglik + 2 * npar, bic = -2 * e$loglik + log(sum(w)) * npar,
       gamma = e$gamma, iterations = iter, converged = converged)
}

# 다중 초기값 적합. 같은 응답 궤적을 가진 개체는 하나로 묶어 빈도를 가중치로 쓴다(우도 동일, 속도 향상).
lta_compress <- function(Y) {
  code <- Y; code[is.na(code)] <- 9; key <- apply(mat(code, dim(Y)[1], prod(dim(Y)[-1])), 1, paste, collapse = '')
  first <- !duplicated(key); inv <- match(key, key[first])
  list(Y = Y[first, , , drop = FALSE], w = as.vector(table(inv)), inv = inv)
}
lta_fit <- function(Y, K, nstart = N_START, seed = SEED, init = NULL, w = NULL, ...) {
  cp <- lta_compress(Y); wc <- if (is.null(w)) cp$w else w
  fits <- lapply(seq_len(nstart), function(s) lta_fit_once(cp$Y, K, w = wc, seed = seed + s, init = if (s == 1) init else NULL, ...))
  ll <- vapply(fits, function(f) f$loglik, 0); okc <- vapply(fits, function(f) f$converged, TRUE)
  pool <- if (any(okc)) which(okc) else seq_along(fits); best <- fits[[pool[which.max(ll[pool])]]]
  ord <- order(colMeans(mat(best$theta[1, , ], dim(Y)[3], K)))       # 상태 번호: 평균 응답확률 오름차순
  best$pi <- best$pi[ord]; best$A <- best$A[, ord, ord, drop = FALSE]; best$theta <- best$theta[, , ord, drop = FALSE]
  best$gamma <- best$gamma[cp$inv, , ord, drop = FALSE]
  best$n_converged <- sum(okc); best$n_replicated <- sum(abs(ll - best$loglik) < 1e-6 * (1 + abs(best$loglik))); best
}
lta_occupancy <- function(pi, A) {                                   # 모형 함의 상태 비중 δ_t
  out <- mat(0, dim(A)[1] + 1, length(pi)); out[1, ] <- pi
  for (t in seq_len(dim(A)[1])) out[t + 1, ] <- out[t, ] %*% mat(A[t, , ], length(pi), length(pi)); out
}
lr_test <- function(restricted, full) {                              # 포함관계 모형의 우도비 검정
  stat <- 2 * (full$loglik - restricted$loglik); df <- full$npar - restricted$npar
  c(LR = stat, df = df, p = pchisq(max(stat, 0), df, lower.tail = FALSE))
}

# ── 3. 상태 수 선택 ───────────────────────────────────────────────────────────────────
t0 <- Sys.time()
fits <- lapply(K_GRID, function(K) {
  f <- lta_fit(Y, K, nstart = if (K == 1) 1 else N_START, maxit = MAXIT_SEL)
  cat(sprintf('  K = %d 적합 완료: 로그우도 %.3f, BIC %.1f (누적 %.0f초)\n', K, f$loglik, f$bic, as.numeric(difftime(Sys.time(), t0, units = 'secs')))); f })
sel <- data.frame(K = K_GRID, loglik = sapply(fits, `[[`, 'loglik'), npar = sapply(fits, `[[`, 'npar'),
                  AIC = sapply(fits, `[[`, 'aic'), BIC = sapply(fits, `[[`, 'bic'),
                  converged_starts = sapply(fits, `[[`, 'n_converged'), best_replicated = sapply(fits, `[[`, 'n_replicated'))
K_SEL <- sel$K[which.min(sel$BIC)]; best <- fits[[which(K_GRID == K_SEL)]]
cat(sprintf('BIC 최소: K = %d (%.0f초)\n', K_SEL, as.numeric(difftime(Sys.time(), t0, units = 'secs')))); print(sel, digits = 8)
write.csv(sel, file.path(OUT, 'r_model_selection.csv'), row.names = FALSE)

# ── 4. 측정불변성과 전이 동질성 ───────────────────────────────────────────────────────
warm <- list(pi = best$pi, A = best$A, theta = best$theta)
free <- lta_fit(Y, K_SEL, invariant = FALSE, init = warm, seed = 2204)        # 응답확률 시점별 자유
hom  <- lta_fit(Y, K_SEL, homog = TRUE, seed = 3304,                           # 모든 구간 같은 전이행렬
                init = { w0 <- warm; w0$A[] <- rep(apply(warm$A, c(2, 3), mean), each = TT - 1); w0 })
reg  <- lta_fit(Y, K_SEL, a_groups = REGIMES, seed = 4404,                     # 두 국면
                init = { w1 <- warm; for (g in unique(REGIMES)) { ix <- which(REGIMES == g); m <- apply(warm$A[ix, , , drop = FALSE], c(2, 3), mean); for (t in ix) w1$A[t, , ] <- m }; w1 })
tests <- rbind(`동질 vs 구간별 자유(총괄)` = lr_test(hom, best), `동질 vs 두 국면(초점)` = lr_test(hom, reg),
               `두 국면 vs 구간별 자유` = lr_test(reg, best))
cat(sprintf('측정불변성: 자유화 모형 BIC - 불변 모형 BIC = %.2f (양수면 불변 모형이 유리)\n', free$bic - best$bic)); print(round(tests, 4))

# ── 5. 부트스트랩(개인 궤적 재표집, 선택 K 고정) ──────────────────────────────────────
cp <- lta_compress(Y); set.seed(20261106)
cat('부트스트랩', N_BOOT, '회...\n')
boots <- lapply(seq_len(N_BOOT), function(b) {
  wb <- as.vector(rmultinom(1, N, cp$w / N))                          # 패턴 빈도를 다항 재표집 = 개인 재표집
  f <- lta_fit_once(cp$Y, K_SEL, w = wb, init = warm, tol = 1e-8, maxit = 2000)
  ord <- order(colMeans(mat(f$theta[1, , ], J, K_SEL)))
  list(theta = f$theta[1, , ord], A = f$A[, ord, ord, drop = FALSE], occ = lta_occupancy(f$pi[ord], f$A[, ord, ord, drop = FALSE]), ok = f$converged)
})
boots <- boots[vapply(boots, function(b) b$ok, TRUE)]
qci <- function(key, p) apply(simplify2array(lapply(boots, `[[`, key)), seq_along(dim(boots[[1]][[key]])), quantile, probs = p)
SL <- if (K_SEL == 3) c('S1 저소비', 'S2 구독 중심', 'S3 복합 구매') else paste0('S', seq_len(K_SEL))
prof <- data.frame(item = rep(ITEMS, K_SEL), state = rep(SL, each = J), estimate = as.vector(best$theta[1, , ]),
                   ci_low = as.vector(qci('theta', .025)), ci_high = as.vector(qci('theta', .975)))
trans <- expand.grid(t = seq_len(TT - 1), from = seq_len(K_SEL), to = seq_len(K_SEL))
trans$estimate <- best$A[cbind(trans$t, trans$from, trans$to)]
trans$ci_low <- qci('A', .025)[cbind(trans$t, trans$from, trans$to)]; trans$ci_high <- qci('A', .975)[cbind(trans$t, trans$from, trans$to)]
trans$interval <- paste0(WAVES[trans$t], '→', WAVES[trans$t + 1]); trans$from_state <- SL[trans$from]; trans$to_state <- SL[trans$to]
occ <- data.frame(wave = rep(WAVES, K_SEL), state = rep(SL, each = TT), estimate = as.vector(lta_occupancy(best$pi, best$A)),
                  ci_low = as.vector(qci('occ', .025)), ci_high = as.vector(qci('occ', .975)))
write.csv(prof, file.path(OUT, 'r_response_profiles.csv'), row.names = FALSE)
write.csv(trans[, c('interval', 'from_state', 'to_state', 'estimate', 'ci_low', 'ci_high')], file.path(OUT, 'r_transition_probabilities.csv'), row.names = FALSE)

# ── 6. 그림(RStudio Plots 창에 차례로 표시하고 figures/ 에 PNG 저장) ──────────────────
if (requireNamespace('ggplot2', quietly = TRUE)) {
  library(ggplot2)
  fam <- if (.Platform$OS.type == 'windows') { windowsFonts(`Malgun Gothic` = windowsFont('Malgun Gothic')); 'Malgun Gothic' } else ''   # 한글 글꼴
  COL <- c('#2a78d6', '#eb6834', '#1baf7a', '#eda100')[seq_len(K_SEL)]; names(COL) <- SL
  note <- if (DATA_MODE == 'synthetic') '모의자료(설계 보정) · 실증 추정치 아님' else NULL
  th0 <- theme_minimal(base_size = 11, base_family = fam) + theme(panel.grid.minor = element_blank(), legend.position = 'top',
                                                                 plot.caption = element_text(colour = 'grey50', size = 8))
  ITEM_KO <- c(paid_app = '유료 앱 구입', inapp_item = '앱 내 아이템 구입', paid_video = '영상 유료 이용', paid_music = '음악 유료 이용')
  prof$item <- factor(ITEM_KO[prof$item], ITEM_KO[ITEMS]); prof$state <- factor(prof$state, SL); occ$state <- factor(occ$state, SL)
  trans$from_state <- factor(trans$from_state, rev(SL)); trans$to_state <- factor(trans$to_state, SL)
  lta_plots <- list(
    model_selection = ggplot(sel, aes(K, BIC)) + geom_line(colour = COL[1], linewidth = 1) + geom_point(colour = COL[1], size = 3) +
      geom_point(data = sel[sel$K == K_SEL, ], shape = 1, size = 7) + labs(x = '잠재상태 수 K', y = 'BIC(작을수록 좋음)', caption = note) + th0,
    profiles = ggplot(prof, aes(item, estimate, colour = state)) +
      geom_pointrange(aes(ymin = ci_low, ymax = ci_high), position = position_dodge(width = .5), linewidth = .7) +
      scale_colour_manual(values = COL) + ylim(0, 1) + labs(x = NULL, y = '상태별 응답확률', colour = NULL, caption = note) + th0,
    transitions = ggplot(trans, aes(to_state, from_state, fill = estimate)) + geom_tile(colour = 'white', linewidth = 1) +
      geom_text(aes(label = sprintf('%.3f\n(%.3f–%.3f)', estimate, ci_low, ci_high), colour = estimate > .55), size = 2.9, family = fam) +
      scale_colour_manual(values = c('black', 'white'), guide = 'none') + scale_fill_gradient(low = '#f4f8fd', high = '#123f78', limits = c(0, 1)) +
      facet_wrap(~interval, nrow = 1) + labs(x = '도착 상태', y = '출발 상태', fill = '전이확률', caption = note) + th0 +
      theme(axis.text.x = element_text(size = 7)),
    occupancy = ggplot(occ, aes(wave, estimate, colour = state, fill = state)) + geom_ribbon(aes(ymin = ci_low, ymax = ci_high), alpha = .15, colour = NA) +
      geom_line(linewidth = 1) + geom_point(size = 2) + scale_colour_manual(values = COL) + scale_fill_manual(values = COL) +
      labs(x = NULL, y = '상태 비중(모형 함의)', colour = NULL, fill = NULL, caption = note) + th0)
  for (nm in names(lta_plots)) {
    if (interactive()) print(lta_plots[[nm]])                        # RStudio Plots 창에 표시
    ggsave(file.path(FIG, paste0('r_', nm, '.png')), lta_plots[[nm]], width = if (nm == 'transitions') 11 else 7, height = 4, dpi = 160, bg = 'white')
  }
  cat('그림 객체는 lta_plots 리스트에 남아 있습니다. 예: lta_plots$profiles\n')
} else cat('ggplot2 가 없어 그림은 건너뜁니다: install.packages("ggplot2")\n')

# ── 7. 교차검증 표: R EM · LMest · (노트북이 읽어) 파이썬 ─────────────────────────────
cross <- data.frame(quantity = c('loglik_het', 'npar_het', 'bic_het', 'loglik_hom', 'loglik_regime', 'loglik_free_theta', 'K'),
                    source = 'R_EM', value = c(best$loglik, best$npar, best$bic, hom$loglik, reg$loglik, free$loglik, K_SEL))
if (requireNamespace('LMest', quietly = TRUE)) {
  cat('LMest 로 같은 사양(K =', K_SEL, ', 구간별 전이, 불변 응답확률, 결측 MAR) 적합 중...\n')
  long <- data.frame(id = rep(seq_len(N), TT), time = rep(seq_len(TT), each = N))
  for (j in seq_len(J)) long[[ITEMS[j]]] <- as.vector(Y[, , j])
  long <- long[order(long$id, long$time), ]
  fml <- as.formula(paste(paste(ITEMS, collapse = ' + '), '~ NULL'))
  lm0 <- tryCatch(LMest::lmest(responsesFormula = fml, index = c('id', 'time'), data = long, k = K_SEL, modBasic = 0,
                               start = 0, tol = 1e-10, maxit = 5000, seed = SEED),
                  error = function(e) { cat('LMest 실행 실패:', conditionMessage(e), '\n'); NULL })
  if (!is.null(lm0)) {
    cross <- rbind(cross, data.frame(quantity = c('loglik_het', 'npar_het', 'bic_het'), source = 'LMest',
                                     value = c(lm0$lk, lm0$np, lm0$bic)))
    psi1 <- lm0$Psi[2, , ]; ord <- order(rowMeans(psi1))             # LMest 의 P(Y=1|상태), 상태 정렬
    cat(sprintf('LMest 로그우도 %.4f vs R EM %.4f (차이 %.2e)\n', lm0$lk, best$loglik, abs(lm0$lk - best$loglik)))
    cat(sprintf('응답확률 최대 절대차 %.2e, 전이확률 최대 절대차 %.2e\n', max(abs(psi1[ord, ] - t(best$theta[1, , ]))),
                max(abs(aperm(lm0$Pi[ord, ord, -1, drop = FALSE], c(3, 1, 2)) - best$A))))
    cross <- rbind(cross, data.frame(quantity = c('max_abs_diff_theta_vs_R', 'max_abs_diff_A_vs_R'), source = 'LMest',
                                     value = c(max(abs(psi1[ord, ] - t(best$theta[1, , ]))),
                                               max(abs(aperm(lm0$Pi[ord, ord, -1, drop = FALSE], c(3, 1, 2)) - best$A)))))
  }
} else cat('LMest 미설치 → 패키지 대조는 건너뜁니다: install.packages("LMest")\n')
write.csv(cross, file.path(OUT, 'r_crosscheck.csv'), row.names = FALSE)
pyf <- file.path(OUT, 'python_estimates.json')
if (file.exists(pyf) && requireNamespace('jsonlite', quietly = TRUE)) {
  py <- jsonlite::fromJSON(pyf)
  cat(sprintf('파이썬 로그우도 %.4f vs R EM %.4f (차이 %.2e)\n', py$loglik_het, best$loglik, abs(py$loglik_het - best$loglik)))
  cat(sprintf('응답확률 최대 절대차 %.2e\n', max(abs(py$theta - best$theta[1, , ]))))
}
print(cross, digits = 10)
cat('완료. 표: outputs/r_*.csv, 그림: figures/r_*.png\n')
