M = linspace(0, 2000, 200);
beams = [0.03, 1.2e-4; 0.05, 9e-5; 0.07, 6e-5];
figure; hold on;
for k = 1:size(beams,1)
  c = beams(k,1);
  I = beams(k,2);
  sigma = (M .* c) ./ I;
  plot(M, sigma, 'LineWidth', 2);
end
xlabel('Bending moment M');
ylabel('Stress sigma');
title('Beam bending: sigma = M*c/I');
grid on;
legend('c=0.03, I=1.2e-4', 'c=0.05, I=9e-5', 'c=0.07, I=6e-5', 'Location', 'northwest');
saveas(gcf, fullfile('outputs', 'beam_stress.png'));
disp('Saved outputs/beam_stress.png');
